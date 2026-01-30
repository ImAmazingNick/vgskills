# Video Generator - Quick Reference Card

## The ONE Command You Need

```bash
vg request generate --file <request.md>
```

**With existing video:**
```bash
vg request generate --file <request.md> --skip-record --video <existing.mp4>
```

**No request file?** → AI generates one (see SKILL.md Workflow D)

---

## Command Cheatsheet

| Action | Command |
|--------|---------|
| Full video from request | `vg request generate --file demo.md` |
| Record browser | `vg record --url <url> --scenario ai-agent` |
| Generate speech | `vg audio tts --text "..." -o audio.mp3` |
| Add audio to video | `vg compose sync --video v.mp4 --audio a.mp3 -o final.mp4` |
| Timeline audio | `vg compose distribute --video v.mp4 --request r.md --audio-dir audio/ -o final.mp4` |
| Trim | `vg edit trim --video v.mp4 --start 5 --end 60 -o out.mp4` |
| Speed up | `vg edit speed --video v.mp4 --factor 2 -o fast.mp4` |
| Speed silence | `vg edit speed-silence --video v.mp4 --factor 3 -o out.mp4` |
| Talking head | `vg talking-head generate --audio a.mp3 -o presenter.mp4` |
| Optimize | `vg quality optimize --input v.mp4 -o small.mp4 --quality medium` |

---

## Iterative Workflow (No Request File)

1. Extract URL, goal, auth from user prompt
2. Create request.md with draft narration
3. `vg request generate --file request.md` → get timeline
4. Refine narration based on actual timing
5. `vg request generate --file request.md --skip-record --video demo.mp4`

---

## Required Environment

```bash
ELEVENLABS_API_KEY=...  # TTS
FAL_API_KEY=...         # Talking heads
```

---

## Output Location

`videos/runs/<run_id>/final.mp4`

---

## Error? Check This

| Error | Fix |
|-------|-----|
| `AUTH_ERROR` | API keys missing |
| `FILE_NOT_FOUND` | Wrong path |
| `TRANSIENT` | Retry |

---

## More Info

- `SKILL.md` - Full AI Agent guide
- `VIDEO_GENERATOR_CAPABILITIES.md` - Complete reference
