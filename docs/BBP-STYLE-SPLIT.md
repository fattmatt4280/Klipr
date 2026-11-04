# BBP vs Brand Style - Split (1A-LITE Step 5)
Design only in this commit. No QA code, no endpoints, no new table.
Purpose: a QA failure must say which list it broke, so a safety failure
is never confused with a style preference, and a style preference is
never presented as a safety rule.
## bbp_rules - universal, safety
These apply to any AI shop footage portraying a working professional,
regardless of brand. A failure here fails the whole cut.
- bbp_machine_barrier: every machine fully sheathed in a clear barrier bag.
- bbp_bottles_bagged: every squeeze / wash bottle bagged.
- bbp_surfaces_covered: every armrest, chair, and tray covered with
  plastic wrap or dental bibs.
- bbp_gloves_worn: gloves on every hand in frame.
Note what is NOT in this list: glove color and machine choice are NOT
safety rules. They are brand style, below. A clip with blue gloves is
not a BBP failure - it is a Shyftd.ink style failure (if that brand is
the target), and must be reported that way.
## brand_style_rules - Shyftd.ink (example brand, user-controlled)
These are brand-kit controlled, not universal. They can change per brand
without changing safety rules, and they do not apply to other brands
unless that brand adopts them.
- style_glove_color: gloves neon green or black only, never blue/purple.
- style_machine: wireless black pen-style machine with battery pack
  (Critical / Cheyenne Unlimited type), no cords, wrapped in clear or
  black tubing.
- style_machine_default: if no machine is specified, use the machine above.
## Storage in 1A-LITE (no new table)
- bbp_rules: stored in templates.recipe JSON (shared, per template).
- brand_style_rules: stored in brands.brand_kit JSON (per brand).
- A future rules table is deferred (see docs/DEFERRED.md). Do not add
  a rules table in 1A-LITE to implement this split.
## QA failure format (design, for Step 6 QA)
A QA result must include, at minimum:
- list: "bbp_rules" or "brand_style_rules"
- rule_id: e.g. "bbp_gloves_worn" or "style_glove_color"
- asset_id / render_id, and a human-readable note naming the frame / beat.
Example, in words not code: "FAILED bbp_rules / bbp_gloves_worn - hand
in frame without gloves" vs "FAILED brand_style_rules / style_glove_color -
gloves are blue, Shyftd.ink requires neon green or black".
A BBP failure fails the whole cut. A style failure fails that brand's
cut, and is reported as style, not safety.
## Relationship to standing rules
The standing BBP rule from 2026-09-27 is refined, not replaced, by this
split: barrier / bottle / cover / gloves-worn are safety; glove color
and machine choice are Shyftd.ink style. The original rule text is
preserved in memory; this file is the 1A-LITE implementation of that
refinement for QA purposes.
