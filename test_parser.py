from manuscript_parser import extract_text
t, e = extract_text('sample/synthetic_manuscript_1.pdf', 'synthetic_manuscript_1.pdf')
if t:
    print('SUCCESS')
    print('Length:', len(t))
else:
    print('FAILED:', e)
