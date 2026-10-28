---
name: mcp-bulk-tests
description: >-
  Creates one custom skill per MCP server, plus a bulk tool-call YAML file and
  a bulk agent-prompt YAML file, after confirming real usage. Use when the user
  wants a skill, harness pack, bulk tool calls, or bulk agent prompts to test
  an MCP server.
---

# Bulk MCP test skill

Create one custom skill for exactly one MCP server, then the YAML that skill describes. A second server gets a second skill and a second pair of YAML files.

This skill is for one MCP server only. Do not add calls or prompts for any other server.

Do not fill gaps from the schema. A field the user did not give is left out of the YAML. Schema defaults, examples, and descriptions are not copied into `arguments` or prompts. If a required field is missing, that call is not written until the user supplies the value.

Write nothing until the user confirms the read-back.

## Steps

1. Ask question 1. If they name more than one server, stop and start a separate skill for each.
2. Analyze that server only. It must already exist in `config/targets.yaml`. Run `sonar tools list`, then `sonar tools describe` for every tool on that target. Show name, description, and which fields the server marks required. That list is the menu for later questions. It is not a source of argument values.
3. Ask questions 2–9, one at a time. Say the impact sentence with the question. Go to the next question only after that answer is in.
4. Read back the planned `calls` and `prompts`. Wait for a yes.
5. Write the three files below from the confirmed answers only.

## Questions

1. "Which one target in config/targets.yaml is this skill for?"
   Impact: that name is the only `target:` in both YAML files. Any other server is a different skill. Nothing for a second server is written here.

2. "These are the tools on that server: [names from tools/list]. Which ones should have direct calls in the batch file?"
   Impact: each name you pick becomes one or more `calls[].tool` entries in `<name>.batch.yaml`. Names you leave out do not appear there.

3. "Which tools must never be called, even if a prompt would make that tempting?"
   Impact: those names are listed as forbidden in the custom `SKILL.md`. They get no `calls` entry and no prompt that would need them. Sonar does not enforce this at runtime; the files simply omit them.

4. "For tool `<name>`, paste the argument object a real call uses. Required fields are: [from describe]. I will not fill any field you leave out, including schema defaults."
   Impact: the object you paste is copied into `calls[].arguments` for that tool. A required field you skip means that call is omitted until you provide it. Nothing from the tool schema is substituted.

5. "In what order should these calls run?"
   Impact: that order is the order of `calls:` in the batch YAML, and the order `sonar tools batch` runs them. Each call starts a new connection. A later call does not see the previous call's server state. If a later call needs a value from an earlier result, you paste that value into that call's arguments in question 4.

6. "Type the sentences a real user would send. One sentence per line. I will copy the words unchanged into a double-quoted YAML string."
   Impact: each line becomes one double-quoted entry in `prompts:` in `<name>.prompts.yaml`. The words are not rewritten into "call tool X". Quoting keeps a colon, a date, or the word yes from being turned into something other than text. The prompt count starts as the number of lines you give.

7. "For this prompt: `<sentence>`. Which batch calls should the agent make, in what order, and what does a good answer look like in one sentence?"
   Impact: the call list and the good-answer sentence go into the custom `SKILL.md` so a harness knows the expected behavior. They are not turned into checks inside either YAML. The batch file stays `calls`. The prompts file stays the sentences from question 6. A call you name here that was not selected in question 2 is added only after you also paste its arguments (question 4).

8. "Which calls or prompts need extra copies, and which single field changes in each copy? Example: the same call with three different ids. Say none if you want only what you already gave."
   Impact: each extra value adds one duplicated call in the batch YAML and, when you tie it to a prompt, one duplicated prompt with only that detail changed. No other field is varied. "None" means the files contain only the examples you already confirmed.

9. "What is the skill name, and which directory should I write it to? Default is `<repo>/.cursor/skills/<name>/`."
   Impact: file paths and the skill `name` only. It does not change `calls` or `prompts`. The description names this one target.

## Files

Write into the directory from question 9. Default is `<repo>/.cursor/skills/<name>/`.

- `SKILL.md` — custom skill. Fill the template below.
- `<name>.batch.yaml` — `target` plus `calls: [{tool, arguments}]`, in the order from question 5.
- `<name>.prompts.yaml` — one real user sentence per `prompts` entry, each a double-quoted YAML string. Matching direct calls stay in the batch file.

Shape example only. Do not copy `everything-stdio` or these words onto a real server:

```yaml
target: everything-stdio
prompts:
  - "Say hello back to me with the message hello."
```

```yaml
target: everything-stdio
calls:
  - tool: echo
    arguments:
      message: hello
```

## Custom skill template

```markdown
---
name: <name>
description: >-
  Bulk tool calls and bulk agent prompts for the <target> MCP server only.
  Use when extending or regenerating that server's batch and prompts YAML.
---

# <name>

This skill is for one MCP server only: <target>. Do not add calls or prompts for any other server.

Do not fill gaps from the schema. Use only the argument values and prompts written below.

## In bounds

- Tools: <confirmed tools and argument objects>
- Forbidden: <names from question 3, or none>

## Scenarios

For each confirmed prompt:

- Prompt: <sentence, unchanged>
- Calls, in order: <tool and arguments>
- Good answer: <one sentence>
- Variants: <the question 8 rule, or none>

## Files

Write or extend `<name>.batch.yaml` and `<name>.prompts.yaml` next to this skill, still for <target>.

- Batch shape: `target`, then `calls: [{tool, arguments}]`.
- Prompts shape: `target`, then `prompts:` as a list of double-quoted sentences.

Prompts stay in the user's voice. If a request needs a field or a tool that is not in the confirmed scenarios, ask before writing.

Run when the user wants the pack executed:

    sonar tools batch --file <name>.batch.yaml
    sonar agent batch --file <name>.prompts.yaml
```
