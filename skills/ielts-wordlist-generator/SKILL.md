# IELTS WordList Generator

## Purpose

Given English words, generate one valid JSON WordList for this IELTS vocabulary-review application. Focus on useful IELTS meanings and usage rather than complete dictionary coverage.

## Required structure

Each Word contains:

- `id`: unique lowercase ID, normally `<word>_001`; replace spaces with `_`.
- `word`: original English word.
- `phonetic`: common IPA pronunciation.
- `senses`: one or more IELTS-relevant senses.
- `notes`: short practical usage advice when useful; otherwise `""`.

Each sense contains:

- `pos`: part of speech such as `n.`, `v.`, `adj.`, `adv.`.
- `english_meaning`: concise English definition. It may be `""` when an English definition is unavailable.
- `chinese_meaning`: concise Chinese meaning for this sense.
- `example`: natural IELTS-level English example sentence.
- `example_translation`: accurate Chinese translation of the example.
- `synonyms`: useful IELTS synonyms or near-synonyms.
- `collocations`: common and useful collocations.

## Rules

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
11. Output valid JSON only when the user asks for a WordList data file.

## Example

```json
{
  "schema_version": 1,
  "name": "IELTS Education Vocabulary",
  "description": "雅思教育类常用词汇",
  "words": [
    {
      "id": "address_001",
      "word": "address",
      "phonetic": "/əˈdres/",
      "senses": [
        {
          "pos": "v.",
          "english_meaning": "to deal with or take action on a problem or difficult situation",
          "chinese_meaning": "处理；应对，尤指问题或困难",
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
