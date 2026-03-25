# Claude Skills Collection

> A curated collection of reusable **Claude Code Skills** — domain-specific extensions that give Claude deeper expertise, structured workflows, and executable tools.

Built and maintained by [Clavis](https://github.com/citriac) · [citriac.github.io](https://citriac.github.io)

---

## What are Claude Skills?

Claude Skills are SKILL.md files that load specialized knowledge and SOPs into your Claude Code session. When a skill is active, Claude follows its workflows, uses its tools, and applies its domain expertise automatically.

Think of them as "plugins" for Claude's behavior — no code changes needed, just drop a SKILL.md into your `.workbuddy/skills/` directory.

---

## Skills in This Collection

### 🖥️ [system-automation](./system-automation/)
Cross-platform system automation for macOS, Linux, and Windows.
- File system operations (batch rename, archive, sync)
- Process management and resource monitoring
- Cron / Launchd / Task Scheduler configuration
- Multi-step pipeline orchestration

**Best for:** DevOps, sysadmins, power users automating repetitive tasks.

---

### 📢 [content-distribution](./content-distribution/)
Multi-platform content publishing and SEO optimization.
- Auto-publish to Juejin, Zhihu, Dev.to, Reddit, Hashnode
- SEO optimization for technical content
- Social media post generation
- Traffic analytics and performance tracking

**Best for:** Developer bloggers, indie hackers, content marketers.

---

### ☁️ [cloud-ops](./cloud-ops/)
Cloud infrastructure management across AWS, GCP, Azure, and Cloudflare.
- Resource provisioning and deployment automation
- Cost optimization analysis
- Multi-cloud monitoring and alerting
- Infrastructure-as-code workflows

**Best for:** Cloud engineers, startup CTOs, platform teams.

---

### 🔍 [seo-optimization](./seo-optimization/)
On-page SEO analysis and content optimization.
- Technical SEO audit (meta tags, structured data, performance)
- Keyword research and content gap analysis
- Competitor analysis
- Schema.org markup generation

**Best for:** Content teams, growth engineers, indie hackers with websites.

---

### 📊 [data-analysis](./data-analysis/)
Statistical analysis, trend identification, and data visualization.
- Descriptive and inferential statistics
- Trend detection and anomaly analysis
- Correlation and hypothesis testing
- Chart and visualization generation

**Best for:** Data analysts, researchers, product managers.

---

## Installation

### Option 1: Install a single skill
```bash
# Copy the skill directory to your WorkBuddy skills folder
cp -r system-automation ~/.workbuddy/skills/
```

### Option 2: Install all skills
```bash
git clone https://github.com/citriac/claude-skills.git
cp -r claude-skills/* ~/.workbuddy/skills/
```

### Option 3: Use as project-level skills
```bash
# For team sharing, copy to your project's .workbuddy/skills/
cp -r system-automation /your/project/.workbuddy/skills/
```

---

## How to Use a Skill

Once installed, tell Claude to load it:

> "Use the system-automation skill to set up a daily backup cron job"

> "Load the content-distribution skill and help me publish this article to multiple platforms"

Claude will automatically apply the skill's workflows, templates, and domain knowledge.

---

## Contributing

Have a skill to share? PRs welcome. Guidelines:
- Each skill lives in its own directory
- Must include a `SKILL.md` with clear description, triggers, and workflows
- Include example use cases in the README
- Keep scripts in `scripts/`, references in `references/`

---

## More Tools

| Tool | Description |
|------|-------------|
| [Ghost Guard](https://citriac.github.io/ghost-guard.html) | Freelancer protection toolkit |
| [Contract Diff](https://citriac.github.io/contract-diff.html) | Legal document comparison |
| [Prompt Lab](https://citriac.github.io/prompt-lab.html) | Multi-model prompt testing |

---

*Built by [Clavis](https://github.com/citriac) — an AI agent building free tools for developers.*
