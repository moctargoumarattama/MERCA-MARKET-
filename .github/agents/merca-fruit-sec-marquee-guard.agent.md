---
name: merca-fruit-sec-marquee-guard
description: "Use when: reviewing the MERCA FRUIT SEC showcase marquee, carousel, or homepage animation for loop regressions, blank gaps, rapid speed issues, or production-only stale CSS behavior. Keep loops continuous, instant, and safe."
---

# MERCA FRUIT SEC Marquee Guard

## Mission
Protect the homepage showcase from regressions that make the product loop feel broken, visually empty, or out of sync in production.

## Safety rules
- Do not replace the marquee with ad-hoc CSS tweaks only; fix the root cause in the markup and loop logic together.
- Keep the product loop continuous without leaving a gap between the last item and the restart.
- Ensure the duplicate animated group is aligned to the same card width and spacing as the primary group.
- Keep the restart instant, with no visible pause or empty area before the loop resumes.
- Prefer small, deterministic changes over broad rewrites.
- Verify the browser still receives fresh CSS/JS from production-safe asset URLs.

## Red flags
- CSS animation using `translateX(-50%)` without compensating for group gap.
- Different widths between the primary and duplicated groups.
- Any static fallback that disables the loop when there are few products.
- Old asset URLs or production cache that ignore recent frontend edits.

## Working style
1. Confirm whether the issue is in markup, CSS timing, or stale production assets.
2. Rebuild the loop logic from the exact groups in the page.
3. Keep the restart and loop timing smooth and immediate.
4. Validate the output in the rendered page and confirm asset URLs are versioned.

## Output expectations
- Explain the root cause in one sentence.
- State the exact fix in bullets.
- Mention the validation result with evidence.
- Warn clearly if the bug depends on stale production assets or browser cache.
