# Caption Styles Reference

> **Version**: 1.0  
> **Last Updated**: January 2026  
> **Purpose**: Caption style presets and customization guide

---

## Overview

This file contains built-in caption styles for the video-generator. Styles are defined using markdown tables for easy editing and consistency with the existing MD-based architecture.

### Usage

**CLI**:
```bash
# Use a built-in preset
vg captions burn --video final.mp4 --captions captions.srt --style youtube

# Available presets: youtube, professional, tiktok, accessibility
```

**Request File (Inline Override)**:
```markdown
## Caption Style

**Preset:** professional

_Or define custom:_

| Setting | Value |
|---------|-------|
| Font | Montserrat |
| Font Size | 26 |
| Color | white |
| Outline | 2px black |
| Position | bottom-center |
```

---

## Built-in Style Presets

### youtube

Standard YouTube caption style - white text with black outline, positioned at bottom center. Good for general-purpose videos.

| Setting | Value |
|---------|-------|
| Font | Arial |
| Font Size | 24 |
| Color | white |
| Outline | 2px black |
| Shadow | 1px |
| Position | bottom-center |
| Margin Bottom | 40px |
| Max Chars/Line | 42 |
| Max Lines | 2 |

**Best For**: General videos, tutorials, product demos, educational content

---

### professional

Clean professional style for corporate and business videos. Subtle styling with clear readability.

| Setting | Value |
|---------|-------|
| Font | Helvetica |
| Font Size | 22 |
| Color | white |
| Outline | 1px black |
| Shadow | none |
| Position | bottom-center |
| Margin Bottom | 30px |
| Max Chars/Line | 50 |
| Max Lines | 2 |

**Best For**: Corporate videos, presentations, executive demos, webinars

---

### tiktok

Bold, eye-catching style for vertical social media videos. Large text positioned at top with heavy outline.

| Setting | Value |
|---------|-------|
| Font | Impact |
| Font Size | 36 |
| Color | white |
| Outline | 3px black |
| Shadow | 2px |
| Position | top-center |
| Margin Top | 200px |
| Max Chars/Line | 20 |
| Max Lines | 3 |

**Best For**: TikTok, Instagram Reels, YouTube Shorts, vertical social media content

---

### accessibility

High contrast style optimized for accessibility. Yellow text on black outline for maximum readability.

| Setting | Value |
|---------|-------|
| Font | Arial |
| Font Size | 28 |
| Color | yellow |
| Outline | 3px black |
| Shadow | 2px |
| Position | bottom-center |
| Margin Bottom | 50px |
| Max Chars/Line | 40 |
| Max Lines | 2 |

**Best For**: Accessibility compliance, hard-of-hearing audiences, high-visibility requirements

---

## Style Settings Reference

### Font
System font name (e.g., Arial, Helvetica, Impact, Times New Roman)

**Common Options**:
- `Arial` - Clean, universal sans-serif
- `Helvetica` - Professional sans-serif
- `Impact` - Bold, attention-grabbing
- `Verdana` - Highly readable on screen
- `Georgia` - Elegant serif

### Font Size
Size in pixels (e.g., 22, 24, 28, 36)

**Guidelines**:
- `18-22` - Small, unobtrusive
- `24-28` - Standard, readable
- `32-40` - Large, social media style
- `42+` - Extra large, short-form content

### Color
Text color (color name or hex)

**Options**:
- `white` - Standard, works on most backgrounds
- `yellow` - High contrast, accessibility
- `black` - Light backgrounds only
- `red`, `blue`, `green` - Brand colors

### Outline
Outline thickness and color (e.g., "2px black", "3px #1a1a1a")

**Guidelines**:
- `1px` - Subtle definition
- `2px` - Standard readability
- `3-4px` - Heavy contrast for busy backgrounds

### Shadow
Drop shadow size (e.g., "1px", "2px", "none")

**Options**:
- `none` - Clean, minimal
- `1px` - Subtle depth
- `2px` - Strong definition

### Position
Caption placement on screen

**Options**:
- `bottom-center` - Standard subtitle position
- `top-center` - Social media style
- `center` - Centered on screen
- `bottom-left`, `bottom-right` - Corner placement

### Margin Bottom / Margin Top
Distance from screen edge in pixels

**Guidelines**:
- `20-40px` - Close to edge
- `40-60px` - Standard positioning
- `80-200px` - Away from edge (for social media)

### Max Chars/Line
Maximum characters per line before wrapping

**Guidelines**:
- `20-30` - Short lines (mobile/vertical)
- `40-50` - Standard (desktop/horizontal)
- `60+` - Long lines (wide content)

### Max Lines
Maximum number of lines per caption

**Guidelines**:
- `1-2` - Standard subtitles
- `3-4` - Social media, longer captions

---

## Customization Guide

### Method 1: Edit CAPTIONS.md

Add a new style section to this file:

```markdown
### my_custom_style

Description of when to use this style.

| Setting | Value |
|---------|-------|
| Font | Montserrat |
| Font Size | 26 |
| Color | white |
| Outline | 2px #1a1a1a |
| Shadow | 1px |
| Position | bottom-center |
| Margin Bottom | 35px |
| Max Chars/Line | 45 |
| Max Lines | 2 |
```

Then use it:
```bash
vg captions burn --video final.mp4 --captions captions.srt --style my_custom_style
```

### Method 2: Inline in Request File

Add a "Caption Style" section to your request MD file:

```markdown
## Caption Style

**Preset:** professional

_Customize:_

| Setting | Value |
|---------|-------|
| Font Size | 28 |
| Color | #e0e0e0 |
```

This will use the `professional` preset but override font size and color.

### Method 3: Per-Command Override

Pass style parameters directly (future enhancement):
```bash
vg captions burn --video final.mp4 --captions captions.srt \
  --font Arial --font-size 26 --color white --outline "2px black"
```

---

## Technical Reference

### FFmpeg Subtitle Filter

The caption burn-in uses FFmpeg's `subtitles` filter with `force_style` parameter. The style settings are converted to ASS subtitle format.

**Example FFmpeg Command**:
```bash
ffmpeg -i video.mp4 \
  -vf "subtitles=captions.srt:force_style='FontName=Arial,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3,Outline=2,Shadow=1,MarginV=40,Alignment=2'" \
  -c:a copy \
  output.mp4
```

### ASS Color Format

Colors in ASS format use BGR hex with alpha:
- `&HFFFFFF&` - White
- `&H00FFFF&` - Yellow
- `&H000000&` - Black
- `&H0000FF&` - Red
- `&HFF0000&` - Blue
- `&H00FF00&` - Green

### Alignment Values

ASS alignment (numpad layout):
```
7 (top-left)      8 (top-center)      9 (top-right)
4 (middle-left)   5 (middle-center)   6 (middle-right)
1 (bottom-left)   2 (bottom-center)   3 (bottom-right)
```

### Border Style

- `1` - Outline + drop shadow
- `3` - Opaque box (recommended for subtitles)
- `4` - Opaque box with reduced transparency

---

## Best Practices

### Readability
- Use high contrast (white text on black outline)
- Avoid busy fonts for long captions
- Test on different screen sizes
- Ensure minimum 2 characters per second reading speed

### Positioning
- Keep captions in "safe zone" (away from edges)
- Don't cover important visual content
- Consider platform requirements (YouTube vs TikTok)
- Leave room for progress bars/controls

### Text Length
- Keep lines under 42 characters (standard subtitle width)
- Limit to 2 lines per caption for readability
- Split long sentences into multiple captions
- Sync caption changes with natural speech pauses

### Style Selection
- **YouTube/Vimeo**: Use `youtube` or `professional`
- **TikTok/Reels**: Use `tiktok` style
- **Corporate**: Use `professional` style
- **Accessibility**: Use `accessibility` style
- **Custom Brand**: Create custom style with brand fonts/colors

---

## Examples

### Example 1: Standard Product Demo
```bash
vg captions burn --video demo.mp4 --captions captions.srt --style youtube
```

### Example 2: Executive Presentation
```bash
vg captions burn --video presentation.mp4 --captions captions.srt --style professional
```

### Example 3: Social Media Short
```bash
vg captions burn --video reel.mp4 --captions captions.srt --style tiktok
```

### Example 4: Accessibility-Compliant
```bash
vg captions burn --video training.mp4 --captions captions.srt --style accessibility
```

---

## Troubleshooting

### Captions Don't Appear
- Verify SRT file format is correct
- Check FFmpeg version (needs subtitle filter support)
- Ensure font is available on system
- Try a different style preset

### Text is Cut Off
- Reduce `Max Chars/Line` setting
- Increase margins from edges
- Use smaller font size
- Check video resolution

### Captions Are Blurry
- Use higher resolution source video
- Increase font size
- Add stronger outline
- Avoid excessive compression

### Reading Speed Too Fast
- Split long captions into shorter segments
- Increase audio segment duration
- Add pauses between segments
- Validate with `vg captions preview`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-29 | Initial release with 4 built-in styles |

---

*For more information, see the [Video Generator SKILL documentation](../SKILL.md)*
