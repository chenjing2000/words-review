# IELTS WordList Generator

## Purpose

Given English words, generate one valid JSON WordList for this IELTS vocabulary-review application. Focus on useful IELTS meanings and usage rather than complete dictionary coverage.

## Required structure

Each Word contains:

- `wid`: unique lowercase Word ID. Normally derive it from the English word using simple lowercase letters, digits, and `_`; replace spaces or punctuation separators with `_`. Keep it short and stable. If two words would produce the same `wid`, add a short numeric suffix such as `_2`.
- `word`: original English word.
- `phonetic`: common IPA pronunciation.
- `senses`: one or more IELTS-relevant senses.
- `notes`: short practical usage advice when useful; otherwise `""`.

Each sense contains:

- `pos`: part of speech such as `n.`, `v.`, `adj.`, `adv.`.
- `english_meaning`: concise English definition. It may be `""` when an English definition is unavailable.
- `chinese_meaning`: concise Chinese meaning for this sense.
- `eid`: Example ID for this English example. When `example` is non-empty, `eid` must contain exactly 6 random digits, for example `501372`. Digits may start with `0`, so always keep `eid` as a string rather than a JSON number.
- `example`: natural IELTS-level English example sentence.
- `example_translation`: accurate Chinese translation of the example.
- `synonyms`: useful IELTS synonyms or near-synonyms.
- `collocations`: common and useful collocations.

## ID rules

1. Every `wid` must be unique within the WordList.
2. Every visible `word` must also be unique within the WordList, ignoring letter case. Put multiple meanings of the same spelling under one Word's `senses` instead of creating duplicate Word entries.
3. Every non-empty `eid` must be unique within the entire WordList.
4. Generate `eid` as a JSON string containing exactly 6 random digits whenever an English `example` is generated.
5. While generating the WordList, keep a temporary `used_eids` set. If a newly generated `eid` is already in the set, generate another six-digit value until it is unique, then add it to the set.
6. If an English `example` is regenerated or replaced, generate a new `eid` at the same time.
7. If only `example_translation` changes and the English `example` itself does not change, keep the existing `eid`.
8. If `example` is empty or absent, `eid` may be absent or `""`; these are the only normal states for a sense without an example.
9. If a sense has an English example but `eid` is missing or empty, append a brief data warning to the Word-level `notes`, such as `数据提示：sense 2 例句缺少 eid。`
10. If a sense has an English example but its non-empty `eid` is not exactly 6 digits, append a brief data warning such as `数据提示：sense 2 例句 eid 无效。`
11. If a sense has no English example but has a non-empty `eid`, append a brief data warning such as `数据提示：sense 2 无例句但存在 eid。`
12. Data warnings are appended to existing `notes`; never overwrite useful original notes.

## Content rules

1. Prefer meanings commonly useful in IELTS reading, writing, listening, or speaking.
2. Do not add rare meanings merely to make an entry comprehensive.
3. Put different important meanings or parts of speech in separate `senses`.
4. Keep `english_meaning` clear and concise. Prefer common English words and do not define the target word by simply repeating it.
5. Keep `chinese_meaning` accurate and concise.
6. Examples should be natural and academically appropriate, not artificially complicated.
7. `example_translation` should translate the example directly without extra explanation.
8. Synonyms and collocations should be genuinely useful in real IELTS contexts.
9. Keep `notes` brief and practical.
10. Do not generate review counts, study status, or other user-learning data.
11. After the final `words` array is complete, append the exact number of words to the WordList `name` in parentheses. For example, if the final array contains 223 words, use `"IELTS Band 7+ Vocabulary (223)"`. Count the actual final array length, not the requested or estimated quantity, and append the count only once. If a draft name already ends with a count, replace that count with the final value instead of adding another one.
12. Keep `schema_version` equal to `1`.
13. Output valid JSON only when the user asks for a WordList data file.

## Example

```json
{
  "schema_version": 1,
  "name": "IELTS Education Vocabulary (1)",
  "description": "雅思教育类常用词汇",
  "words": [
    {
      "wid": "address",
      "word": "address",
      "phonetic": "/əˈdres/",
      "senses": [
        {
          "pos": "v.",
          "english_meaning": "to deal with or take action on a problem or difficult situation",
          "chinese_meaning": "处理；应对，尤指问题或困难",
          "eid": "482731",
          "example": "Governments should address the underlying causes of educational inequality.",
          "example_translation": "政府应当解决教育不平等的根本原因。",
          "synonyms": ["tackle", "deal with", "confront"],
          "collocations": ["address a problem", "address an issue", "address concerns"]
        }
      ],
      "notes": "IELTS 写作中常作动词使用。"
    }
  ]
}
```
