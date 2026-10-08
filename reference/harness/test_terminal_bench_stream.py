"""CPU-only checks: legitimate hex data, real repetition, and SSE integrity."""
import json, unittest
from iq3s_stability_replay import StreamEvidence, StopRun
from terminal_bench_stream import TerminalBenchEvidence

class StreamTests(unittest.TestCase):
    def evidence(self, source='0'*160, role='user'):
        return TerminalBenchEvidence(0, {'messages':[{'role':role,'content':source}]})
    def feed(self, e, text, kind='reasoning_content'):
        for c in text:
            e.event(json.dumps({'choices':[{'delta':{kind:c}}]}), 1)
    def test_grounded_inline_hex_and_incomplete_still_rejected(self):
        e=self.evidence();self.feed(e, 'Page data: `'+ '0'*160 +'` then decode.')
        self.assertEqual(e.metrics()['zero_quote_exemptions'][0]['length'],160)
        with self.assertRaisesRegex(StopRun,'incomplete_SSE'):e.validate()
        e.event(json.dumps({'choices':[{'delta':{},'finish_reason':'stop'}],
                            'usage':{'completion_tokens':50},'timings':{'predicted_n':50}}),2)
        e.event('[DONE]',3);e.validate()
    def test_real_loops_remain_stopped(self):
        for text in ['0'*128, '`'+'0'*161, '`'+'!'*128, 'alpha beta '*128]:
            with self.subTest(text=text[:15]), self.assertRaises(StopRun):self.feed(self.evidence(),text)
    def test_no_source_or_assistant_source_cannot_exempt(self):
        for source,role in [('', 'user'),('0'*160,'assistant')]:
            with self.subTest(role=role),self.assertRaises(StopRun):self.feed(self.evidence(source,role),'`'+'0'*128)
    def test_long_input_does_not_lift_hard_cap(self):
        with self.assertRaises(StopRun):self.feed(self.evidence('0'*5000),'`'+'0'*513)
    def test_request_budget(self):
        e=self.evidence()
        with self.assertRaisesRegex(StopRun,'quote_budget'):
            for i in range(30):self.feed(e, str(i)+' `'+('0'*160)+'`\n')
    def test_content_supported(self):
        e=self.evidence();self.feed(e,'`'+'0'*160+'`','content')
        self.assertEqual(len(e.quotes),1)
    def test_base_guard_unchanged(self):
        with self.assertRaisesRegex(StopRun,'repeated_character_128'):self.feed(StreamEvidence(0),'`'+'0'*128)
    def test_api_error_still_stops(self):
        with self.assertRaisesRegex(StopRun,'API_error'):self.evidence().event('{"error":"failure"}',1)

    def test_wrapped_hex_input_has_same_512_cap(self):
        source='ab' * 16 + '0'*128 + '\n' + '0'*160 + '\n' + '0'*160 + '\n' + '0'*100
        e=self.evidence(source)
        self.assertEqual(e.zero_limit,512)
        self.feed(e,'`'+'0'*512)
        with self.assertRaisesRegex(StopRun,'repeated_character'):self.feed(e,'0')

    def test_wrapped_input_preserves_incomplete_detection(self):
        e=self.evidence('0'*160+'\n'+'0'*40,role='tool')
        self.assertEqual(e.zero_limit,200)
        self.feed(e,'`'+'0'*162+'`')
        with self.assertRaisesRegex(StopRun,'incomplete_SSE'):e.validate()

    def test_wrapping_requires_full_width_byte_lines(self):
        for source in ['0'*128+'\n'+'0'*128, '0'*160+'\n\n'+'0'*160,
                       '0'*160+'\nnot hex\n'+'0'*160, '0'*160+'\n'+'0'*159]:
            with self.subTest(source=source[-10:]):
                e=self.evidence(source)
                self.assertLessEqual(e.zero_limit,160)
                with self.assertRaises(StopRun):self.feed(e,'`'+'0'*161)

    def test_wrapped_input_cannot_exempt_other_loops(self):
        source='0'*160+'\n'+'0'*160
        for text in ['0'*128,'`'+'!'*128,'```'+'0'*128,'alpha beta '*128]:
            with self.subTest(text=text[:10]),self.assertRaises(StopRun):self.feed(self.evidence(source),text)
        with self.assertRaises(StopRun):self.feed(self.evidence(source,'assistant'),'`'+'0'*128)

    def test_wrapped_budget_unchanged(self):
        e=self.evidence(('0'*160+'\n')*4)
        with self.assertRaisesRegex(StopRun,'quote_budget'):
            for i in range(9):self.feed(e,str(i)+' `'+('0'*512)+'`\n')

if __name__=='__main__':unittest.main()
