"""Bounded, input-grounded hex quotation handling for Terminal-Bench only."""
import re
from iq3s_stability_replay import StreamEvidence, repetition_reason

POLICY = 'input_grounded_inline_zero_hex_v2_wrapped160'

def wrapped_hex_sources(source):
    """Reconstruct only complete hex-byte lines wrapped at Harbor's 160 columns."""
    group = []
    for line in source.splitlines() + ['']:
        is_hex = bool(re.fullmatch(r'[0-9a-fA-F]+', line)) and len(line) % 2 == 0
        if is_hex and len(line) == 160:
            group.append(line)
            continue
        if group and is_hex and 0 < len(line) < 160:
            group.append(line)
        if len(group) > 1:
            yield ''.join(group)
        group = []

class TerminalBenchEvidence(StreamEvidence):
    def __init__(self, start, request):
        super().__init__(start)
        sources = [m.get('content', '') for m in request.get('messages', [])
                   if m.get('role') in ('user', 'tool') and isinstance(m.get('content', ''), str)]
        sources += [joined for source in sources for joined in wrapped_hex_sources(source)]
        self.zero_limit = min(512, max((len(m.group()) for s in sources
                                      for m in re.finditer(r'0{128,}', s)), default=0))
        self.quotes = {}

    def check_repetition(self, text, key):
        reason = repetition_reason(text)
        if reason != 'repeated_character_128' or key not in ('0:reasoning', '0:content'):
            return reason
        masks = []
        for m in re.finditer(r'([^\s])\1{127,}', text):
            prefix = text[:m.start()].rsplit('\n', 1)[-1]
            if (m.group(1) != '0' or len(m.group()) > self.zero_limit
                    or '```' in prefix or prefix.count('`') % 2 != 1
                    or not re.search(r'(?<!`)`[0-9a-fA-F]*$', prefix)):
                return reason
            absolute = self.chars[key.split(':')[1]] - len(text) + m.start()
            self.quotes[(key, absolute)] = len(m.group())
            masks.append(m.span())
        if sum(self.quotes.values()) > 4096:
            return 'input_grounded_hex_quote_budget_4096'
        # Keep phrase-loop detection and all non-exempt character checks.
        for start, end in reversed(masks):
            text = text[:start] + '0' + text[end:]
        return repetition_reason(text)

    def metrics(self):
        return {**super().metrics(), 'repetition_policy': POLICY,
                'input_zero_quote_limit': self.zero_limit,
                'zero_quote_exemptions': [{'channel':k, 'offset':p, 'length':n}
                                          for (k,p),n in self.quotes.items()]}
