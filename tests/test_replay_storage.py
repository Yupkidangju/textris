"""시계 해상도와 게시 경쟁에 영향을 받지 않는 리플레이 보존 계약."""
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from textris.replay import OWN_NAME, ReplayStore
from textris.session import Session


class ReplayStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=ReplayStore(self.tmp.name)
        self.now=datetime(2026,10,8,12,30,0,999999)

    def replay(self,seed):
        session=Session(seed=seed)
        session.command('drop'); session.step()
        return session.replay()

    def test_frozen_clock_retains_latest_twenty_distinct_saves(self):
        with patch('textris.replay.datetime',wraps=datetime) as clock:
            clock.now.return_value=self.now
            names=[self.store.save(self.replay(seed)) for seed in range(22)]
        self.assertNotIn(None,names)
        self.assertEqual(len(set(names)),22)
        self.assertTrue(all(OWN_NAME.fullmatch(name) for name in names))
        self.assertEqual(names,sorted(names))
        self.assertEqual(self.store.list(),list(reversed(names[-20:])))
        self.assertEqual(len(list(self.store.directory.glob('*.json'))),20)
        self.assertEqual([self.store.load(name)['seed'] for name in self.store.list()],
                         list(range(21,1,-1)))
        self.assertFalse(list(self.store.directory.glob('*.tmp')))

    def test_clock_repeat_or_reversal_preserves_existing_bytes_across_instances(self):
        with patch('textris.replay.datetime',wraps=datetime) as clock:
            clock.now.return_value=self.now
            first=self.store.save(self.replay(1))
            self.assertIsNotNone(first)
            path=self.store.directory/first
            original=path.read_bytes()
            repeated=ReplayStore(self.tmp.name).save(self.replay(2))
            self.assertEqual(path.read_bytes(),original)
            clock.now.return_value=self.now-timedelta(days=1)
            reversed_name=ReplayStore(self.tmp.name).save(self.replay(3))
            self.assertEqual(path.read_bytes(),original)
        self.assertEqual(len({first,repeated,reversed_name}),3)
        self.assertGreater(repeated,first)
        self.assertGreater(reversed_name,repeated)
        self.assertEqual([self.store.load(name)['seed'] for name in self.store.list()],[3,2,1])

    def test_destination_created_during_publication_is_not_replaced(self):
        publish=os.rename if os.name=='nt' else os.link
        payload=self.replay(1)
        raced=[]

        def race(source,target):
            if not raced:
                self.assertEqual(self.store.list(),[])
                self.assertEqual(json.loads(Path(source).read_text(encoding='utf-8')),payload)
                Path(target).write_bytes(b'concurrent replay bytes')
                raced.append(Path(target))
            return publish(source,target)

        with patch('textris.replay.datetime',wraps=datetime) as clock:
            clock.now.return_value=self.now
            with patch('os.rename' if os.name=='nt' else 'os.link',side_effect=race):
                name=self.store.save(payload)
        self.assertIsNotNone(name)
        self.assertEqual(len(raced),1)
        self.assertEqual(raced[0].read_bytes(),b'concurrent replay bytes')
        self.assertGreater(name,raced[0].name)
        self.assertEqual(self.store.load(name)['seed'],1)
        self.assertFalse(list(self.store.directory.glob('*.tmp')))

    def test_publication_failure_preserves_existing_files_and_cleans_temporary(self):
        first=self.store.save(self.replay(1))
        path=self.store.directory/first
        original=path.read_bytes()
        with patch('os.rename' if os.name=='nt' else 'os.link',
                   side_effect=OSError('publication unavailable')):
            self.assertIsNone(self.store.save(self.replay(2)))
        self.assertEqual(self.store.warning,'replay_error')
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(self.store.list(),[first])
        self.assertFalse(list(self.store.directory.glob('*.tmp')))

    def test_persistent_publication_contention_is_bounded_and_leaves_no_files(self):
        with patch('os.rename' if os.name=='nt' else 'os.link',
                   side_effect=FileExistsError('concurrent destination')) as publish:
            self.assertIsNone(self.store.save(self.replay(1)))
        self.assertEqual(publish.call_count,128)
        self.assertEqual(self.store.warning,'replay_error')
        self.assertEqual(list(self.store.directory.iterdir()),[])

    def test_concurrent_stores_keep_each_replay(self):
        payloads=[self.replay(seed) for seed in range(8)]
        with patch('textris.replay.datetime',wraps=datetime) as clock:
            clock.now.return_value=self.now
            with ThreadPoolExecutor(max_workers=8) as workers:
                names=list(workers.map(lambda data: ReplayStore(self.tmp.name).save(data),payloads))
        self.assertNotIn(None,names)
        self.assertEqual(len(set(names)),8)
        self.assertEqual([self.store.load(name)['seed'] for name in names],list(range(8)))
        self.assertFalse(list(self.store.directory.glob('*.tmp')))

    @unittest.skipUnless(os.name=='nt','Windows namespace comparisons')
    def test_extended_dos_namespace_accepts_only_paths_inside_root(self):
        name='replay-20261008-123000-000000.json'
        target=self.store.directory/name
        extended=Path('\\\\?\\'+str(target))
        with patch.object(Path,'resolve',return_value=extended):
            self.assertEqual(self.store._path(name),target)
        outside=self.store.root.parent/(self.store.root.name+'-outside')/'replays'/name
        with patch.object(Path,'resolve',return_value=Path('\\\\?\\'+str(outside))):
            with self.assertRaises(ValueError): self.store._path(name)
        self.store.root=Path('\\\\?\\'+str(self.store.root))
        with patch.object(Path,'resolve',return_value=target):
            self.assertEqual(self.store._path(name),target)

    @unittest.skipUnless(os.name=='nt','Windows namespace comparisons')
    def test_extended_unc_namespace_and_device_paths_keep_root_boundary(self):
        name='replay-20261008-123000-000000.json'
        self.store.root=Path('\\\\server\\share\\data')
        self.store.directory=self.store.root/'replays'
        cases=[('\\\\?\\UNC\\server\\share\\data\\replays\\'+name,True),
               ('\\\\?\\UNC\\server\\share\\data-outside\\replays\\'+name,False),
               ('\\\\?\\UNC\\server\\other-share\\data\\replays\\'+name,False),
               ('\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1\\'+name,False),
               ('\\\\.\\C:\\data\\replays\\'+name,False)]
        for resolved,allowed in cases:
            with self.subTest(resolved=resolved),patch.object(Path,'resolve',return_value=Path(resolved)),patch.object(Path,'is_symlink',return_value=False):
                if allowed: self.assertEqual(self.store._path(name),self.store.directory/name)
                else:
                    with self.assertRaises(ValueError): self.store._path(name)

    def test_hardlink_publication_branch_preserves_completed_content(self):
        with patch('textris.replay.os',SimpleNamespace(name='posix',link=os.link)):
            first=self.store.save(self.replay(1))
            self.assertIsNotNone(first)
            original=(self.store.directory/first).read_bytes()
            second=self.store.save(self.replay(2))
        self.assertIsNotNone(second)
        self.assertNotEqual(first,second)
        self.assertEqual((self.store.directory/first).read_bytes(),original)
        self.assertEqual(self.store.load(second)['seed'],2)
        self.assertFalse(list(self.store.directory.glob('*.tmp')))
