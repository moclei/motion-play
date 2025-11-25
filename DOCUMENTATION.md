# Motion Play Documentation Guide

This document explains how documentation is organized in the Motion Play project and where to find or create documentation.

## Documentation Structure

```
docs/
├── INDEX.md                          # Master index - start here to find all docs
├── initiatives/                      # Cross-cutting features and major work
│   └── data-collection/
│       ├── README.md                # Initiative overview and entry point
│       ├── tech_reqs.md             # Requirements documents
│       ├── technical_design_doc.md  # Design specifications
│       ├── implementation_plan.md   # Implementation planning
│       ├── PROJECT_STATUS.md        # Current progress tracking
│       ├── guides/                  # Step-by-step implementation guides
│       │   ├── phase1-connectivity-guide.md
│       │   ├── phase2-data-pipeline-guide.md
│       │   └── phase3-*.md
│       └── work/                    # Temporary working documents (delete when done)
├── references/                      # Hardware datasheets and vendor documentation
│   ├── vcnl4040/                   # Organized by component name
│   ├── pca9546a/
│   └── i2c-multiplexer/
└── archive/                         # Historical documents kept for reference
```

## Quick Navigation

### Primary Entry Points

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) | Project overview, current status, getting started | Humans (developers, contributors) |
| [.context/PROJECT.md](.context/PROJECT.md) | Comprehensive technical reference and context | AI assistants |
| [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) | Quick setup and deployment | New developers |
| [docs/INDEX.md](docs/INDEX.md) | Master documentation index | Everyone |

### Sub-Project Documentation

Each major sub-project has its own README:
- **Firmware**: [firmware/README.md](firmware/README.md) - ESP32-S3 firmware details
- **Frontend**: [frontend/motion-play-ui/README.md](frontend/motion-play-ui/README.md) - React web interface
- **Infrastructure**: [infrastructure/README.md](infrastructure/README.md) - AWS setup and deployment
- **Lambda**: [lambda/README.md](lambda/README.md) - Lambda functions and API

## Where to Find Documentation

### By Topic

**Hardware & PCB Design**
- Component datasheets → `docs/references/[component-name]/`
- PCB schematics → `hardware/pcb-main/kicad/` and `hardware/pcb-sensor/kicad/`
- Pin configurations → `.context/PROJECT.md`

**Firmware Development**
- Architecture overview → `firmware/README.md`
- Component code → `firmware/src/components/`
- Display UI → `firmware/DISPLAY_UI_GUIDE.md`

**Data Collection System**
- Overview → `docs/initiatives/data-collection/README.md`
- Requirements → `docs/initiatives/data-collection/tech_reqs.md`
- Implementation guides → `docs/initiatives/data-collection/guides/`
- Current status → `docs/initiatives/data-collection/PROJECT_STATUS.md`

**Cloud Infrastructure**
- AWS setup → `infrastructure/aws-setup-guide.md`
- Lambda deployment → `infrastructure/lambda-deployment-guide.md`
- Database schema → `infrastructure/DATABASE_SCHEMA.md`

**Web Interface**
- Frontend README → `frontend/motion-play-ui/README.md`
- Component code → `frontend/motion-play-ui/src/components/`

## Where to Create Documentation

### Decision Tree

**New cross-cutting feature or initiative?**
→ Create `docs/initiatives/[initiative-name]/`
- Add README.md as entry point
- Add requirements, design, and planning docs
- Create `guides/` subfolder for implementation guides
- Create `work/` subfolder for temporary/ephemeral docs
- Update `docs/INDEX.md` with new initiative

**Implementation guide for existing initiative?**
→ Add to `docs/initiatives/[initiative-name]/guides/`

**Temporary working document (bug investigation, test notes)?**
→ Add to `docs/initiatives/[initiative-name]/work/`
- **Delete when work is complete**

**Hardware reference material (datasheet, vendor guide)?**
→ Add to `docs/references/[component-name]/`

**Sub-project specific documentation?**
→ Add to the sub-project folder (`firmware/`, `lambda/`, etc.)
- Or update existing README in that folder

**Not sure if document is still useful?**
→ Move to `docs/archive/` for later review

## Documentation Lifecycle

### Permanent Documents
- Requirements and design documents
- Implementation guides
- Technical specifications
- Architecture documentation
- Component datasheets

**Location**: Initiative folders, references, sub-project folders

### Ephemeral Documents
- Bug investigation notes
- Testing checklists (for specific bugs/features)
- Temporary debugging guides
- Work-in-progress notes

**Location**: `docs/initiatives/[name]/work/` folders  
**Lifecycle**: **Delete when work is complete**

### Stale Documents
- Old plans that are no longer relevant
- Historical documentation that might be useful for context
- Superseded guides

**Location**: `docs/archive/`  
**Lifecycle**: Review periodically; delete if truly obsolete

## Creating New Initiatives

When starting a major new feature or cross-cutting work:

1. **Create folder structure**:
   ```
   docs/initiatives/[initiative-name]/
   ├── README.md              # Overview and entry point
   ├── tech_reqs.md          # Optional: Requirements
   ├── technical_design.md   # Optional: Design doc
   ├── guides/               # Implementation guides
   └── work/                 # Temporary/working docs
   ```

2. **Write README.md** with:
   - Initiative overview and objectives
   - Current status
   - Links to key documents
   - Links to related sub-projects

3. **Update docs/INDEX.md**:
   - Add entry in "Active Initiatives" section
   - Include brief description
   - Mention key documents

4. **Create documents as needed**:
   - Requirements, design, implementation plan at root of initiative
   - Implementation guides in `guides/`
   - Working notes in `work/`

## Naming Conventions

- **Folders**: lowercase with hyphens (e.g., `data-collection`)
- **Files**: lowercase with hyphens or underscores (e.g., `tech_reqs.md`, `phase1-guide.md`)
- **README.md**: Always capitalized as shown

## Maintaining Documentation

### When to Update

- **docs/INDEX.md**: When adding/removing initiatives
- **Initiative README**: When status changes or new guides are added
- **Root README.md**: When project status changes significantly
- **.context/PROJECT.md**: When hardware changes or technical architecture evolves

### Documentation Quality

Good documentation should:
- Have a clear purpose and audience
- Be up-to-date with current implementation
- Link to related documents
- Include examples where helpful
- Be concise but complete

## Getting Help

If you're unsure where documentation should go:
1. Check `docs/INDEX.md` for existing initiatives
2. Review this guide's decision tree
3. Look for similar existing documentation
4. When in doubt, ask or put it in the most logical place

---

*For questions about this documentation structure, see DOCUMENTATION_REORGANIZATION.md for the rationale behind these decisions.*

