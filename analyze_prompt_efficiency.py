#!/usr/bin/env python3
"""
Prompt Efficiency Analyzer

Analyzes prompt templates to identify token overspending issues and suggest optimizations.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


def count_tokens_estimate(text: str) -> int:
    """Rough estimate of tokens (1 token ≈ 4 characters for English)."""
    return len(text) // 4


def analyze_repetition(text: str) -> List[Tuple[str, int]]:
    """Find repeated phrases that could be deduplicated."""
    # Find phrases repeated multiple times
    lines = text.split('\n')
    phrase_counts = {}

    for line in lines:
        line = line.strip()
        if len(line) > 20:  # Only consider substantial lines
            phrase_counts[line] = phrase_counts.get(line, 0) + 1

    # Return phrases repeated more than once
    repeated = [(phrase, count) for phrase, count in phrase_counts.items() if count > 1]
    return sorted(repeated, key=lambda x: x[1] * len(x[0]), reverse=True)


def analyze_verbosity(text: str) -> Dict[str, any]:
    """Analyze verbosity patterns."""
    issues = {
        'long_paragraphs': [],
        'redundant_examples': [],
        'excessive_bullets': [],
        'duplicate_instructions': []
    }

    paragraphs = text.split('\n\n')
    for i, para in enumerate(paragraphs):
        # Check for overly long paragraphs
        if len(para) > 500:
            issues['long_paragraphs'].append({
                'index': i,
                'length': len(para),
                'preview': para[:100] + '...'
            })

        # Check for excessive bullet points
        bullets = [line for line in para.split('\n') if line.strip().startswith(('-', '*', '•'))]
        if len(bullets) > 10:
            issues['excessive_bullets'].append({
                'index': i,
                'count': len(bullets),
                'preview': para[:100] + '...'
            })

    return issues


def analyze_references(text: str) -> Dict[str, int]:
    """Count file path references."""
    # Find all file path references
    path_pattern = r'`[^`]*\.(py|json|md|sh|yml|yaml)`'
    paths = re.findall(path_pattern, text)

    # Find directory references
    dir_pattern = r'`[^`]*/[^`]*`'
    dirs = re.findall(dir_pattern, text)

    # Find "Reference:" or "REFERENCE:" mentions
    reference_pattern = r'\*\*Reference\*\*:|Reference:'
    references = re.findall(reference_pattern, text, re.IGNORECASE)

    return {
        'file_references': len(paths),
        'directory_references': len(dirs),
        'explicit_references': len(references)
    }


def find_redundant_sections(text: str) -> List[Dict[str, any]]:
    """Identify sections with similar content."""
    sections = {}
    current_section = None

    for line in text.split('\n'):
        if line.startswith('#'):
            current_section = line.strip()
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)

    # Look for similar content across sections
    redundancies = []
    section_items = list(sections.items())

    for i, (sec1, content1) in enumerate(section_items):
        content1_str = '\n'.join(content1)
        for sec2, content2 in section_items[i+1:]:
            content2_str = '\n'.join(content2)

            # Simple similarity check: count common substantial lines
            lines1 = set(line.strip() for line in content1 if len(line.strip()) > 30)
            lines2 = set(line.strip() for line in content2 if len(line.strip()) > 30)

            if lines1 and lines2:
                overlap = lines1 & lines2
                if len(overlap) > 0:
                    redundancies.append({
                        'section1': sec1,
                        'section2': sec2,
                        'overlap_lines': len(overlap),
                        'examples': list(overlap)[:3]
                    })

    return redundancies


def analyze_prompt_efficiency(prompt_path: Path) -> Dict[str, any]:
    """Comprehensive prompt efficiency analysis."""

    with open(prompt_path, 'r') as f:
        content = f.read()

    analysis = {
        'file': str(prompt_path),
        'total_chars': len(content),
        'total_lines': len(content.split('\n')),
        'estimated_tokens': count_tokens_estimate(content),
        'sections': {},
        'issues': {}
    }

    # Count sections
    sections = [line for line in content.split('\n') if line.startswith('#')]
    analysis['sections'] = {
        'total': len(sections),
        'h1': len([s for s in sections if s.startswith('# ') and not s.startswith('## ')]),
        'h2': len([s for s in sections if s.startswith('## ')]),
        'h3': len([s for s in sections if s.startswith('### ')])
    }

    # Analyze repetition
    repeated = analyze_repetition(content)
    if repeated:
        analysis['issues']['repetition'] = {
            'count': len(repeated),
            'top_repeated': repeated[:5],
            'wasted_tokens_estimate': sum(count_tokens_estimate(phrase) * (count - 1)
                                         for phrase, count in repeated)
        }

    # Analyze verbosity
    verbosity = analyze_verbosity(content)
    analysis['issues']['verbosity'] = verbosity

    # Analyze references
    refs = analyze_references(content)
    analysis['issues']['references'] = refs

    # Find redundant sections
    redundancies = find_redundant_sections(content)
    if redundancies:
        analysis['issues']['redundant_sections'] = redundancies

    # Calculate waste
    total_waste = 0
    if 'repetition' in analysis['issues']:
        total_waste += analysis['issues']['repetition'].get('wasted_tokens_estimate', 0)

    analysis['waste_estimate'] = {
        'tokens': total_waste,
        'percentage': (total_waste / analysis['estimated_tokens'] * 100) if analysis['estimated_tokens'] > 0 else 0
    }

    return analysis


def generate_recommendations(analysis: Dict) -> List[str]:
    """Generate optimization recommendations."""
    recommendations = []

    # Token budget
    tokens = analysis['estimated_tokens']
    if tokens > 3000:
        recommendations.append(f"⚠️ HIGH: Prompt is {tokens} tokens (~{tokens//1000}K). Consider splitting or condensing.")
    elif tokens > 2000:
        recommendations.append(f"⚠️ MEDIUM: Prompt is {tokens} tokens. Could be optimized.")

    # Repetition
    if 'repetition' in analysis['issues']:
        rep = analysis['issues']['repetition']
        wasted = rep.get('wasted_tokens_estimate', 0)
        recommendations.append(f"🔄 REPETITION: {wasted} tokens wasted on {rep['count']} repeated phrases")
        recommendations.append("   → Extract common patterns into a single reference section")

    # Verbosity
    verb = analysis['issues'].get('verbosity', {})
    if verb.get('long_paragraphs'):
        recommendations.append(f"📝 VERBOSITY: {len(verb['long_paragraphs'])} overly long paragraphs (>500 chars)")
        recommendations.append("   → Break into shorter, focused sections")

    if verb.get('excessive_bullets'):
        recommendations.append(f"📋 BULLETS: {len(verb['excessive_bullets'])} sections with >10 bullet points")
        recommendations.append("   → Group related bullets or move to external docs")

    # References
    refs = analysis['issues'].get('references', {})
    total_refs = refs.get('file_references', 0) + refs.get('directory_references', 0)
    if total_refs > 20:
        recommendations.append(f"📁 REFERENCES: {total_refs} file/directory references")
        recommendations.append("   → Consider using a file tree or glob patterns")

    # Redundant sections
    if 'redundant_sections' in analysis['issues']:
        red = analysis['issues']['redundant_sections']
        if red:
            recommendations.append(f"♻️ REDUNDANCY: {len(red)} pairs of sections with overlapping content")
            recommendations.append("   → Consolidate duplicate instructions")

    # Waste
    waste = analysis.get('waste_estimate', {})
    if waste.get('percentage', 0) > 10:
        recommendations.append(f"💰 WASTE: ~{waste['percentage']:.1f}% of tokens are redundant")

    return recommendations


def print_analysis(analysis: Dict):
    """Pretty print analysis results."""
    print("=" * 80)
    print(f"PROMPT EFFICIENCY ANALYSIS: {Path(analysis['file']).name}")
    print("=" * 80)

    print(f"\n📊 STATISTICS:")
    print(f"  Characters: {analysis['total_chars']:,}")
    print(f"  Lines: {analysis['total_lines']:,}")
    print(f"  Estimated Tokens: {analysis['estimated_tokens']:,} (~{analysis['estimated_tokens']//1000}K)")
    print(f"  Sections: {analysis['sections']['total']} (H1: {analysis['sections']['h1']}, "
          f"H2: {analysis['sections']['h2']}, H3: {analysis['sections']['h3']})")

    print(f"\n🎯 RECOMMENDATIONS:")
    recommendations = generate_recommendations(analysis)
    if recommendations:
        for rec in recommendations:
            print(f"  {rec}")
    else:
        print("  ✅ No major issues found!")

    # Detailed issues
    if 'repetition' in analysis['issues']:
        rep = analysis['issues']['repetition']
        print(f"\n🔄 TOP REPEATED PHRASES:")
        for phrase, count in rep['top_repeated'][:5]:
            tokens = count_tokens_estimate(phrase)
            wasted = tokens * (count - 1)
            print(f"  [{count}x, ~{wasted} tokens wasted] {phrase[:80]}...")

    if 'redundant_sections' in analysis['issues']:
        red = analysis['issues']['redundant_sections']
        if red:
            print(f"\n♻️ REDUNDANT SECTIONS:")
            for item in red[:3]:
                print(f"  {item['section1']}")
                print(f"  ↔️ {item['section2']}")
                print(f"  Overlap: {item['overlap_lines']} lines")
                print()

    print(f"\n💰 WASTE ESTIMATE:")
    waste = analysis['waste_estimate']
    print(f"  Redundant tokens: ~{waste['tokens']}")
    print(f"  Waste percentage: {waste['percentage']:.1f}%")
    print(f"  Optimized estimate: ~{analysis['estimated_tokens'] - waste['tokens']} tokens")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_prompt_efficiency.py <path_to_prompt_template>")
        sys.exit(1)

    prompt_path = Path(sys.argv[1])

    if not prompt_path.exists():
        print(f"Error: File not found: {prompt_path}")
        sys.exit(1)

    analysis = analyze_prompt_efficiency(prompt_path)
    print_analysis(analysis)

    print("\n" + "=" * 80)
    print("OPTIMIZATION SUGGESTIONS:")
    print("=" * 80)
    print("""
1. **Remove Redundant References**: Consolidate repeated file path references
2. **Extract Common Patterns**: Create a single "Quick Reference" section
3. **Condense Examples**: Replace verbose examples with concise bullet points
4. **Use Placeholders**: Replace repeated instructions with {{template_variables}}
5. **Link to External Docs**: Move detailed guides to separate files
6. **Prioritize Critical Info**: Front-load essential rules, defer details
7. **Remove Duplicates**: Merge sections with overlapping content
8. **Simplify Language**: Use shorter sentences and fewer adjectives
    """)
