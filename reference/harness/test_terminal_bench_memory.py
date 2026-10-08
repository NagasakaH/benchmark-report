"""Safety checks for staged benchmark memory preparation, with no GPU/API load."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import terminal_bench_runner as b

class MemoryPreparationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.out=self.root/'evidence';self.out.mkdir()
  self.sample={'mem_free':80*2**30,'gpus':[{'mem_info_vram_used':0,'gpu_busy_percent':0}]*2}
  for target,value in [('R',self.root),('resources',Mock(return_value=self.sample)),('check_resources',Mock()),('idle',Mock(return_value=True))]:
   p=patch.object(b,target,value);p.start();self.addCleanup(p.stop)
  p=patch.object(b.time,'sleep');p.start();self.addCleanup(p.stop)
 def test_foreign_model_never_unloaded(self):
  with patch.object(b,'run',return_value='unrelated\nllm-bench-user-image'),patch.object(b.urllib.request,'urlopen') as api:
   with self.assertRaisesRegex(AssertionError,'Unexpected active'):b.prepare_cold_boundary(self.out,'iq3',lambda:None)
   api.assert_not_called()
 def test_busy_previous_model_never_unloaded(self):
  b.idle.return_value=False
  with patch.object(b,'run',return_value=b.CONTAINERS['iq3']),patch.object(b.urllib.request,'urlopen') as api:
   with self.assertRaisesRegex(AssertionError,'busy'):b.prepare_cold_boundary(self.out,'iq3',lambda:None)
   api.assert_not_called()
 def folders(self):
  for name in ['strata-data/packs/iq3_s','strata-data/models/IQ3_S','strata-data/packs/ud-iq4_xs-040-20261007','strata-data/models/UD-IQ4_XS','models/Qwen3.8-27B-MXFP4-mtpfp8','models/Qwen3.8-27B-DFlash2-FP8']:
   p=self.root/name;p.mkdir(parents=True)
   with (p/'weight.bin').open('wb') as f:f.truncate(2**20+1)
 def test_advice_is_scoped_and_does_not_delete_files(self):
  self.folders()
  with patch.object(b,'run',return_value=''),patch.object(b.os,'posix_fadvise',create=True) as advice,patch.object(b.os,'POSIX_FADV_DONTNEED',4,create=True):
   b.prepare_cold_boundary(self.out,None,lambda:None)
   self.assertEqual(advice.call_count,6);self.assertEqual(len(list(self.root.rglob('weight.bin'))),6)
 def test_insufficient_free_ram_blocks_after_preparation(self):
  self.folders();self.sample['mem_free']=69*2**30
  with patch.object(b,'run',return_value=''),patch.object(b.os,'posix_fadvise',create=True),patch.object(b.os,'POSIX_FADV_DONTNEED',4,create=True):
   with self.assertRaisesRegex(AssertionError,'below 70GiB'):b.prepare_cold_boundary(self.out,None,lambda:None)

if __name__=='__main__':unittest.main()
