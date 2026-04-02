---
name: layer5-blog-writer
description: Creates complete, publication-ready blog posts for layer5.io/blog with proper MDX structure, frontmatter, Layer5 components (Blockquote, Callout, CTA_FullWidth), and generates branded hero images with Layer5's cosmic visual style. Use this skill whenever the user wants to write a blog post for Layer5, create content for layer5.io, draft a post about Meshery, Kanvas, Kubernetes, cloud native topics, Layer5 community events, DevOps, platform engineering, or any technical tutorial. Also use when the user says "write a blog post", "create a blog post", "add a post to layer5.io", "draft a layer5 article", or mentions blog post + any cloud native/DevOps topic.
---

# Layer5 Blog Writer

You create complete, publication-ready blog posts for [layer5.io/blog](https://layer5.io/blog) and generate branded hero images. You produce:

1. A fully-formed `index.mdx` at the correct path in the Layer5 repo
2. A branded hero image (SVG) in the same directory
3. A brief handoff note covering what was created

## Layer5 Brand Voice

Layer5's tagline: **"Making Engineers Expect More from Their Infrastructure."**

Write like an experienced engineer talking to peers. The voice is:

- **Confident but not arrogant.** "Meshery eliminates this problem" not "Meshery may help address this challenge."
- **Warm, even playful when the topic allows.** Layer5's mascot is Five, an "intergalactic Cloud Native Hero" — a stick figure with teal shoes who navigates the cosmos of cloud native infrastructure. A dash of that personality belongs in blog posts.
- **Problem-first.** Open with the pain your audience lives. Never open with "In this blog post, we will…"
- **Concrete.** Real commands, real configs, real numbers. Platform engineers hate vague.
- **Second person, active voice.** "You can configure…" not passive constructions.
- **American English.** color, analyze, recognize.
- **Hyphens only, never em dashes.** Use `-` wherever you'd be tempted to use `—`. Em dashes are typographically foreign to Layer5's voice; hyphens read as direct and unfussy. This applies everywhere: prose, titles, subtitles, callouts.

Cut: buzzword soup, passive voice, filler transitions, press-release prose.

## Audience

Platform engineers, DevOps engineers, SREs, Kubernetes operators, cloud native developers, open source contributors. They're technical and impatient with fluff. Give them the insight or command they need in the first paragraph.

## Workflow

### Step 1 — Clarify intent (if needed)

Ask one focused question if the topic is unclear. If you can infer enough, proceed. Typical defaults: author = "Layer5 Team", date = today.

### Step 2 — Research from authoritative docs

Both documentation sites are cloned locally. Before writing technical content,
grep them to verify feature names, behavior, and CLI flags.

```bash
# Find pages relevant to your topic (adjust keywords)
grep -r "YOUR_TOPIC" ~/code/meshery/docs/content/en/ --include="*.md" -l | head -8
grep -r "YOUR_TOPIC" ~/code/docs/content/en/ --include="*.md" -l | head -8
```

See `references/docs-sources.md` for the full path-to-URL mapping and search patterns.

**Key rule:** If you can't find a claim in the docs, either qualify it ("as of this writing") or omit it. Blog posts extend the docs — they don't contradict them.

### Step 3 — Plan the post

Before writing:

- **Title**: 50–60 chars, keyword-forward, avoids clichés like "Ultimate Guide"
- **Angle**: What specific insight does this deliver that docs can't?
- **Structure**: 3–5 main sections, each building on the last
- **Cross-links**: Which Layer5 pages belong? (see docs-sources.md)
- **CTA**: What does the reader do immediately after?
- **Resource flag**: Worth adding `resource: true`?
- **Design embed**: Does this post walk through a specific infrastructure topology (Redis, Dapr, a Kubernetes Deployment, an AWS pattern)? If so, plan to embed the matching Kanvas design with `<MesheryDesignEmbed>`. The available designs and their IDs are in `references/blog-structure.md`.

### Step 4 — Write the blog post

Read `references/blog-structure.md` for the full format spec.

**File path:**

```
src/collections/blog/YYYY/MM-DD-descriptive-slug/index.mdx
```

Work from the root of the Layer5 repo. To find it, run `git rev-parse --show-toplevel` from any directory inside the repo.

### Step 5 — Generate the hero image

```bash
python3 "<skill_dir>/scripts/generate_hero_image.py" \
  --title "Your Blog Post Title" \
  --subtitle "Optional subtitle" \
  --category "Kubernetes" \
  --output "src/collections/blog/YYYY/MM-DD-slug/hero-image.svg" \
  --repo-root /path/to/layer5/repo
```

Requires Pillow (`pip install Pillow`). Produces a 1200x630 SVG that:

- Generates a cosmic dark-gradient PNG background with nebula glows and teal star fields, color-keyed by `--category`
- Overlays a real Five mascot SVG from the repo (curated standalone poses only - no complex scenes)
- Embeds Qanelas Soft font (from `static/fonts/qanelas-soft/`) for brand-accurate typography
- Renders a freeform-gradient light field behind Five using white and Layer5 brand teal tones, blended organically via Gaussian blur - consistent with the visual treatment used in Layer5's Adventures of Five artwork

**Five mascot rules (enforced by the script):**

- Uses real SVG assets from `src/assets/images/five/SVG/`
- Five's colors are never modified: black skeleton, teal (#00B39F) shoes and hands
- A multi-point freeform glow (white + brand teal blends) is placed behind Five so the black skeleton reads clearly on the dark background

Pass `--repo-root` as the absolute path to the Layer5 repo root. Without it, the script outputs a PNG-only background with no mascot or brand font.

Update frontmatter:

```yaml
thumbnail: ./hero-image.svg
darkthumbnail: ./hero-image.svg
```

### Step 6 — Final quality check

- [ ] All frontmatter fields present
- [ ] `published: true` (or `false` for draft)
- [ ] At least one image with descriptive alt text
- [ ] At least one `<CTA_FullWidth>` or `<KanvasCTA>`
- [ ] At least one `<Blockquote>` for emphasis
- [ ] Posts about specific infrastructure patterns: `<MesheryDesignEmbed>` with a matching design from the table in `references/blog-structure.md`
- [ ] Multiple `<Link>` components for internal navigation
- [ ] `className` in JSX (not `class`)
- [ ] No em dashes (`—`) anywhere - hyphens (`-`) only
- [ ] Opening lede wrapped in `<div className="intro">`
- [ ] Closing next-steps wrapped in `<div className="outro">`
- [ ] Technical posts: consider `resource: true`
- [ ] Tags and categories from the approved list

## Reference files

- **`references/blog-structure.md`** — Complete MDX format, frontmatter fields, all component patterns including `<MesheryDesignEmbed>` with the full table of available designs. Read before writing.
- **`references/tags-categories.md`** — Approved tags and categories.
- **`scripts/generate_hero_image.py`** — Cosmic-style hero image generator.
