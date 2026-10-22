import { Problem } from '../types'

export const problems: Problem[] = [
  {
    id: 'longest-substring',
    title: 'Longest Substring Without Repeating Characters',
    category: 'Sliding Window',
    difficulty: 'MEDIUM',
    description:
      'Given a string s, find the length of the longest substring without repeating characters. Return 0 for an empty input.',
    starterCode: `def length_of_longest_substring(s: str) -> int:\n    left = 0\n    best = 0\n    seen = set()\n\n    for right, char in enumerate(s):\n        while char in seen:\n            seen.remove(s[left])\n            left += 1\n        seen.add(char)\n        best = max(best, right - left + 1)\n\n    return best`,
    tests: [
      { input: 'abcabcbb', expected_output: 3 },
      { input: 'bbbbb', expected_output: 1 },
      { input: 'pwwkew', expected_output: 3 },
    ],
  },
  {
    id: 'two-sum',
    title: 'Two Sum',
    category: 'Hash Map',
    difficulty: 'EASY',
    description:
      'Given an array of integers and a target, return indices of the two numbers that add up to target. Assume exactly one solution exists.',
    starterCode: `def two_sum(nums: list[int], target: int) -> list[int]:\n    seen = {}\n\n    for index, value in enumerate(nums):\n        complement = target - value\n        if complement in seen:\n            return [seen[complement], index]\n        seen[value] = index\n\n    return []`,
    tests: [
      { input: [[2, 7, 11, 15], 9], expected_output: [0, 1] },
      { input: [[3, 2, 4], 6], expected_output: [1, 2] },
      { input: [[3, 3], 6], expected_output: [0, 1] },
    ],
  },
  {
    id: 'valid-parentheses',
    title: 'Valid Parentheses',
    category: 'Stack',
    difficulty: 'EASY',
    description:
      'Given a string containing brackets, determine whether every opening bracket is closed by the correct type in the correct order.',
    starterCode: `def is_valid(s: str) -> bool:\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n\n    for char in s:\n        if char in pairs.values():\n            stack.append(char)\n        elif not stack or stack.pop() != pairs[char]:\n            return False\n\n    return not stack`,
    tests: [
      { input: '()', expected_output: true },
      { input: '()[]{}', expected_output: true },
      { input: '(]', expected_output: false },
    ],
  },
]
