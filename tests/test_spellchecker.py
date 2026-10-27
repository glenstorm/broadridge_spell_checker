"""Black-box tests for the spelling checker.

The oracle applies the assignment rules directly to each dictionary word:
one insertion, one deletion, two non-adjacent insertions, two non-adjacent
deletions, or one of each. It does not use the program's deletion index.
"""

import itertools
import random
import subprocess
import sys
import unittest


def lower_ascii(text):
    return "".join(
        chr(ord(ch) - ord("A") + ord("a")) if "A" <= ch <= "Z" else ch for ch in text
    )


def delete_one(text, index):
    return text[:index] + text[index + 1 :]


def delete_two(text, first, second):
    return text[:first] + text[first + 1 : second] + text[second + 1 :]


def lcs_length(left, right):
    previous = [0] * (len(right) + 1)
    for i in range(1, len(left) + 1):
        current = [0] * (len(right) + 1)
        for j in range(1, len(right) + 1):
            if left[i - 1] == right[j - 1]:
                current[j] = previous[j - 1] + 1
            else:
                current[j] = previous[j] if previous[j] >= current[j - 1] else current[j - 1]
        previous = current
    return previous[-1]


def edit_distance(query, word):
    """Return 0, 1, 2, or None under the assignment's edit rules."""
    if query == word:
        return 0
    query_length = len(query)
    word_length = len(word)
    if abs(query_length - word_length) > 2:
        return None

    if word_length == query_length - 1:
        for index in range(query_length):
            if delete_one(query, index) == word:
                return 1
        return None

    if word_length == query_length + 1:
        for index in range(word_length):
            if delete_one(word, index) == query:
                return 1
        return None

    if word_length == query_length - 2:
        for first in range(query_length):
            for second in range(first + 2, query_length):
                if delete_two(query, first, second) == word:
                    return 2
        return None

    if word_length == query_length + 2:
        for first in range(word_length):
            for second in range(first + 2, word_length):
                if delete_two(word, first, second) == query:
                    return 2
        return None

    if lcs_length(query, word) == query_length - 1:
        return 2
    return None


def correct_word(word, entries):
    lowered = lower_ascii(word)
    for _original, folded in entries:
        if folded == lowered:
            return word

    one = []
    two = []
    for original, folded in entries:
        distance = edit_distance(lowered, folded)
        if distance == 1:
            one.append(original)
        elif distance == 2:
            two.append(original)

    chosen = one or two
    if not chosen:
        return "{" + word + "?}"
    if len(chosen) == 1:
        return chosen[0]
    return "{" + " ".join(chosen) + "}"


def is_whitespace(ch):
    return ch in " \t\v\f\r"


def correct_line(line, entries):
    parts = []
    index = 0
    length = len(line)
    while index < length:
        if is_whitespace(line[index]):
            parts.append(line[index])
            index += 1
            continue
        start = index
        while index < length and not is_whitespace(line[index]):
            index += 1
        parts.append(correct_word(line[start:index], entries))
    return "".join(parts)


def dictionary_entries(words):
    entries = []
    seen = set()
    for word in words:
        folded = lower_ascii(word)
        if folded in seen:
            continue
        seen.add(folded)
        entries.append((word, folded))
    return entries


def run_program(program, text):
    completed = subprocess.run(
        [program],
        input=text.encode("ascii"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def render(dictionary_words, text_lines):
    body = []
    if dictionary_words:
        body.append(" ".join(dictionary_words))
    body.append("===")
    body.extend(text_lines)
    body.append("===")
    return "\n".join(body) + "\n"


class SpellCheckerTests(unittest.TestCase):
    program = None

    def assertOutput(self, dictionary_words, text_lines, expected_lines):
        code, stdout, stderr = run_program(
            self.program, render(dictionary_words, text_lines)
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stderr, b"")
        expected = "".join(line + "\n" for line in expected_lines).encode("ascii")
        self.assertEqual(stdout.replace(b"\r\n", b"\n"), expected)

    def assertMatchesOracle(self, dictionary_words, text_lines):
        entries = dictionary_entries(dictionary_words)
        expected = [correct_line(line, entries) for line in text_lines]
        self.assertOutput(dictionary_words, text_lines, expected)

    def test_sample(self):
        self.assertOutput(
            [
                "rain",
                "spain",
                "plain",
                "plaint",
                "pain",
                "main",
                "mainly",
                "the",
                "in",
                "on",
                "fall",
                "falls",
                "his",
                "was",
            ],
            [
                "hte rame in pain fells",
                "mainy oon teh lain",
                "was hints pliant",
            ],
            [
                "the {rame?} in pain falls",
                "{main mainly} on the plain",
                "was {hints?} plaint",
            ],
        )

    def test_adjacent_double_deletion_is_rejected(self):
        # "hints" -> "his" deletes the adjacent letters n and t.
        self.assertMatchesOracle(["his", "hint"], ["hints", "hits"])

    def test_nonadjacent_double_edits(self):
        self.assertMatchesOracle(
            ["ad", "ac", "abdc", "axbycd", "abxycd", "bc"],
            ["abcd", "Abcd", "ac", "ad"],
        )

    def test_one_edit_suppresses_two_edits(self):
        self.assertMatchesOracle(
            ["ad", "ac", "abc", "abdc", "axbycd", "abxycd", "bc", "cats", "cat", "catch"],
            ["abcd", "catc", "catx", "caz"],
        )

    def test_case_and_duplicates(self):
        self.assertMatchesOracle(
            ["Rain", "rain", "RAIN", "Spain", "Cab", "BAC", "cab"],
            ["rain", "RAIN", "rian", "Rian", "abc", "HELLO"],
        )

    def test_whitespace_is_preserved(self):
        self.assertMatchesOracle(
            ["Hello"],
            ["", "   ", "\thello  helo\t", "  Hello   helo  "],
        )

    def test_empty_sections(self):
        code, stdout, stderr = run_program(self.program, "cat\n===\n===\n")
        self.assertEqual(code, 0)
        self.assertEqual(stderr, b"")
        self.assertEqual(stdout.replace(b"\r\n", b"\n"), b"")

        code, stdout, stderr = run_program(self.program, "cat\n===\n\n===\n")
        self.assertEqual(code, 0)
        self.assertEqual(stdout.replace(b"\r\n", b"\n"), b"\n")

        code, stdout, stderr = run_program(self.program, "alpha beta\n")
        self.assertEqual(code, 0)
        self.assertEqual(stdout, b"")

    def test_stops_at_second_separator(self):
        # "zzz" is not within two edits of "hello", so this also checks
        # that input after the second separator is ignored.
        code, stdout, stderr = run_program(self.program, "hello\n===\nzzz\n===\nlater\n")
        self.assertEqual(code, 0)
        self.assertEqual(stderr, b"")
        self.assertEqual(stdout.replace(b"\r\n", b"\n"), b"{zzz?}\n")

    def test_separator_must_be_the_whole_line(self):
        # A line is a separator only when it is exactly "===".
        self.assertMatchesOracle(["hello", "==="], ["hello ===", " === "])

    def test_crlf_and_bom(self):
        payload = b"\xef\xbb\xbfRain\r\n===\r\nrian\r\n===\r\n"
        code, stdout, stderr = run_program_bytes(self.program, payload)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, b"")
        self.assertEqual(stdout.replace(b"\r\n", b"\n"), b"Rain\n")

    def test_dictionary_free_format(self):
        text = "rain   spain\tplain\nplaint\n\npain\n===\nlain\n===\n"
        code, stdout, stderr = run_program(self.program, text)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, b"")
        self.assertEqual(stdout.replace(b"\r\n", b"\n"), b"plain\n")

    def test_length_boundaries(self):
        base = "a" * 50
        self.assertMatchesOracle(
            [
                base,
                base[:49],
                base + "b",
                base[:48] + "xy",
                "b" + base[:24] + "c" + base[24:],
                base[:49] + "z",
            ],
            [base[1:], base + "q", base[:48], "q" + base[2:], base[:49] + "y"],
        )

    def test_transposition_and_replacement(self):
        self.assertMatchesOracle(
            ["the", "cab", "cba", "bac", "falls", "fall", "fells"],
            ["hte", "teh", "abc", "cba", "fells", "fall"],
        )

    def test_single_character_insertions(self):
        self.assertMatchesOracle(
            ["a", "aa", "aaa", "baa", "aba", "aab", "bb"],
            ["a", "b", "aa", "bb"],
        )

    def test_random_against_oracle(self):
        rng = random.Random(20261027)
        alphabet = "abcdefghij"
        for _ in range(40):
            words = []
            for _word in range(25):
                length = rng.randint(1, 7)
                words.append("".join(rng.choice(alphabet) for _ in range(length)))
            # Sprinkle case variants and exact duplicates.
            if words:
                words.append(words[0].upper())
                words.append(words[0])
            lines = []
            for _line in range(6):
                tokens = []
                for _token in range(rng.randint(1, 5)):
                    if rng.random() < 0.5 and words:
                        token = rng.choice(words)
                    else:
                        length = rng.randint(1, 7)
                        token = "".join(rng.choice(alphabet) for _ in range(length))
                    if rng.random() < 0.3:
                        token = token.upper()
                    tokens.append(token)
                gap = rng.choice([" ", "  ", "\t", " \t "])
                lines.append(gap.join(tokens))
            self.assertMatchesOracle(words, lines)

    def test_long_random_words(self):
        rng = random.Random(50)
        alphabet = "abcd"
        words = [
            "".join(rng.choice(alphabet) for _ in range(rng.randint(15, 40)))
            for _ in range(12)
        ]
        lines = []
        for word in words[:6]:
            # One deletion, one insertion, an adjacent double deletion, and a swap.
            if len(word) >= 4:
                lines.append(delete_one(word, 2))
                lines.append(word[:3] + "z" + word[3:])
                lines.append(delete_two(word, 1, 2))
                lines.append(word[1] + word[0] + word[2:])
        self.assertMatchesOracle(words, lines)


def run_program_bytes(program, payload):
    completed = subprocess.run(
        [program],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def reachable(word, alphabet):
    one = set()
    two = set()
    length = len(word)
    for index in range(length):
        one.add(delete_one(word, index))
    for index in range(length + 1):
        for ch in alphabet:
            one.add(word[:index] + ch + word[index:])
    for first in range(length):
        for second in range(first + 2, length):
            two.add(delete_two(word, first, second))

    result_length = length + 2
    for left in range(result_length):
        for right in range(left + 2, result_length):
            for ch_left, ch_right in itertools.product(alphabet, repeat=2):
                chars = []
                cursor = 0
                for position in range(result_length):
                    if position == left:
                        chars.append(ch_left)
                    elif position == right:
                        chars.append(ch_right)
                    else:
                        chars.append(word[cursor])
                        cursor += 1
                two.add("".join(chars))

    for index in range(length):
        base = delete_one(word, index)
        for position in range(len(base) + 1):
            for ch in alphabet:
                candidate = base[:position] + ch + base[position:]
                if candidate != word:
                    two.add(candidate)
    for position in range(length + 1):
        for ch in alphabet:
            base = word[:position] + ch + word[position:]
            for index in range(len(base)):
                candidate = delete_one(base, index)
                if candidate != word:
                    two.add(candidate)

    two -= one
    two.discard(word)
    return one, two


class OracleModelTests(unittest.TestCase):
    def test_generator_agrees_with_distance(self):
        alphabet = "ab"
        words = []
        for length in range(0, 4):
            words.extend("".join(chars) for chars in itertools.product(alphabet, repeat=length))
        for word in words:
            one, two = reachable(word, alphabet)
            for other in words:
                distance = edit_distance(word, other)
                if other == word:
                    self.assertEqual(distance, 0)
                    self.assertNotIn(other, one)
                    self.assertNotIn(other, two)
                elif other in one:
                    self.assertEqual(distance, 1, (word, other))
                elif other in two:
                    self.assertEqual(distance, 2, (word, other))
                else:
                    self.assertNotIn(distance, (0, 1, 2), (word, other, distance))

    def test_mixed_edits_match_lcs(self):
        rng = random.Random(1)
        alphabet = "abc"
        for _ in range(200):
            length = rng.randint(0, 8)
            left = "".join(rng.choice(alphabet) for _ in range(length))
            right = "".join(rng.choice(alphabet) for _ in range(length))
            share = False
            if length:
                deletions = {delete_one(left, i) for i in range(length)}
                share = any(delete_one(right, i) in deletions for i in range(length))
            same = left == right
            self.assertEqual(
                share and not same,
                (not same) and length > 0 and lcs_length(left, right) == length - 1,
            )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: test_spellchecker.py <spellchecker-exe>", file=sys.stderr)
        sys.exit(2)
    SpellCheckerTests.program = sys.argv[1]
    unittest.main(argv=[sys.argv[0]])
