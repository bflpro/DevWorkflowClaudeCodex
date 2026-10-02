#!/usr/bin/env node
// PreToolUse reflex hook: injects a stored lesson into context right before
// the matching tool call. Deterministic, no LLM, fail-open (always exit 0).
// Reflex notes live in .claude/reflexes/*.md — see README.md there.

import { readFileSync, readdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, basename } from 'node:path';
import { tmpdir } from 'node:os';

const EDIT_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit']);

function parseNote(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!m) return null;
  const [, fm, body] = m;
  const lines = fm.split(/\r?\n/);
  const triggers = [];
  for (let i = 0; i < lines.length; i++) {
    const um = lines[i].match(/^use-when:\s*(.*)$/);
    if (!um) continue;
    if (um[1].trim()) triggers.push(um[1].trim());
    for (let j = i + 1; j < lines.length; j++) {
      const lm = lines[j].match(/^\s*-\s+(.+)$/);
      if (!lm) break;
      triggers.push(lm[1].trim());
    }
  }
  return { triggers, body: body.trim() };
}

function globToRegex(glob) {
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') {
        re += '.*';
        i++;
        if (glob[i + 1] === '/') i++;
      } else re += '[^/]*';
    } else if (c === '?') re += '[^/]';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp('^' + re + '$');
}

function triggerMatches(trigger, toolName, toolInput, projectDir) {
  if (trigger.startsWith('bash:')) {
    if (toolName !== 'Bash') return false;
    const spec = trigger.slice(5).trim();
    const rm = spec.match(/^\/(.*)\/([a-z]*)$/s);
    const re = rm ? new RegExp(rm[1], rm[2]) : new RegExp(spec);
    return re.test(toolInput.command || '');
  }
  if (trigger.startsWith('edit:')) {
    if (!EDIT_TOOLS.has(toolName)) return false;
    let p = toolInput.file_path || toolInput.notebook_path || '';
    if (projectDir && p.startsWith(projectDir + '/')) p = p.slice(projectDir.length + 1);
    return globToRegex(trigger.slice(5).trim()).test(p);
  }
  return false;
}

try {
  const input = JSON.parse(readFileSync(0, 'utf8'));
  const toolName = input.tool_name || '';
  const toolInput = input.tool_input || {};
  const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
  const reflexDir = join(projectDir, '.claude', 'reflexes');
  if (!existsSync(reflexDir)) process.exit(0);

  // fire each reflex at most once per session
  const stateFile = join(tmpdir(), `claude-reflexes-${input.session_id || 'nosession'}.json`);
  let fired = [];
  try { fired = JSON.parse(readFileSync(stateFile, 'utf8')); } catch { /* first run */ }

  const messages = [];
  for (const file of readdirSync(reflexDir)) {
    if (!file.endsWith('.md') || file === 'README.md' || fired.includes(file)) continue;
    let note;
    try { note = parseNote(readFileSync(join(reflexDir, file), 'utf8')); } catch { continue; }
    if (!note || !note.triggers.length) continue;
    if (note.triggers.some((t) => triggerMatches(t, toolName, toolInput, projectDir))) {
      messages.push(`⚠️ REFLEX [${basename(file, '.md')}]: ${note.body}`);
      fired.push(file);
    }
  }

  if (messages.length) {
    try { writeFileSync(stateFile, JSON.stringify(fired)); } catch { /* dedupe is best-effort */ }
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        additionalContext: messages.join('\n\n'),
      },
    }));
  }
} catch { /* fail-open: a broken hook must never wedge a session */ }
process.exit(0);
