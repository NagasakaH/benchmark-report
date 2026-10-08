"""Only StopRun, repetition_reason and StreamEvidence extracted from the historical helper."""
import json
import re

class StopRun(RuntimeError):
    pass


def repetition_reason(text):
    """Conservative catastrophic-loop checks; preserve false-positive evidence."""
    if re.search(r'([^\s])\1{127,}', text):
        return 'repeated_character_128'
    # A long exact repeated word phrase is suspicious even without punctuation.
    # Require 1 KiB and >=32 repeats; normal source indentation is excluded.
    for n in range(2, 65):
        unit = text[-n:]
        if len(unit.strip()) < 2:
            continue
        count = max(32, (1024 + n - 1) // n)
        if len(text) >= n * count and text.endswith(unit * count):
            return 'repeated_unit_' + str(n) + '_bytes_' + str(n * count)
    return None


class StreamEvidence:
    def __init__(self, start):
        self.start = start
        self.first = self.last = None
        self.usage = self.timings = None
        self.finishes = []
        self.done = False
        self.chunks = 0
        self.channels = {}
        self.chars = {'content': 0, 'reasoning': 0, 'tool_arguments': 0}

    def event(self, payload, now):
        if payload.strip() == '[DONE]':
            self.done = True
            return
        if self.done:
            raise StopRun('SSE_data_after_DONE')
        item = json.loads(payload)
        if item.get('error'):
            raise StopRun('API_error_event: ' + str(item['error']))
        if item.get('usage') is not None:
            self.usage = item['usage']
        if item.get('timings') is not None:
            self.timings = item['timings']
        meaningful = False
        for choice in item.get('choices', []):
            index = choice.get('index', 0)
            if choice.get('finish_reason') is not None:
                self.finishes.append(choice['finish_reason'])
            delta = choice.get('delta') or {}
            parts = [('content', delta.get('content') or ''),
                     ('reasoning', delta.get('reasoning_content') or delta.get('reasoning') or '')]
            for tc in delta.get('tool_calls') or []:
                function = tc.get('function') or {}
                parts.append(('tool_arguments:' + str(tc.get('index', 0)), function.get('arguments') or ''))
                meaningful = meaningful or bool(function.get('name'))
            for kind, part in parts:
                if not isinstance(part, str):
                    raise StopRun('non_string_SSE_delta')
                if not part:
                    continue
                meaningful = True
                key = str(index) + ':' + kind
                self.chars[kind.split(':')[0]] += len(part)
                self.channels[key] = (self.channels.get(key, '') + part)[-8192:]
                reason = self.check_repetition(self.channels[key], key)
                if reason:
                    raise StopRun(reason + ':' + key)
        if meaningful:
            if self.first is None:
                self.first = now
            self.last = now
            self.chunks += 1

    def check_repetition(self, text, key):
        return repetition_reason(text)

    def validate(self):
        missing = [key for key, valid in [('DONE', self.done), ('finish', bool(self.finishes)),
                   ('usage', bool(self.usage)), ('timings', bool(self.timings))] if not valid]
        if missing:
            raise StopRun('incomplete_SSE_missing_' + '_'.join(missing))

    def metrics(self):
        return dict(ttft_s=None if self.first is None else self.first-self.start,
                    output_span_s=None if self.first is None else self.last-self.first,
                    output_chunks=self.chunks, output_chars=self.chars, usage=self.usage,
                    timings=self.timings, finish_reasons=self.finishes, done=self.done)
