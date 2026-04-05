# Pet Image Tracker

This file tracks:
- which pet state images already exist in [pet_images](/home/phill/projects/telegram-archive-bot/pet_images)
- which images still need to be created
- prompts for action/event images used by the bot

## Naming Model

Living pet state images use this pattern:

`<stage>_<state>.png`

Where:
- `stage` is one of `eggling`, `baby`, `child`, `teen`, `adult`, `elder`
- `state` is one of:
  - `healthy`
  - `hungry`
  - `poopy`
  - `dirty`
  - `restless`
  - `hungry_poopy`
  - `hungry_dirty`
  - `hungry_restless`
  - `poopy_dirty`
  - `poopy_restless`
  - `dirty_restless`
  - `hungry_poopy_dirty`
  - `hungry_poopy_restless`
  - `hungry_dirty_restless`
  - `poopy_dirty_restless`
  - `hungry_poopy_dirty_restless`

Additional fallback/special states:
- `<stage>_critical.png`
- `<stage>_dead.png`

## Existing Images

Currently present in [pet_images](/home/phill/projects/telegram-archive-bot/pet_images):

### Eggling

- `eggling_critical.png`
- `eggling_dead.png`
- `eggling_dirty.png`
- `eggling_dirty_restless.png`
- `eggling_healthy.png`
- `eggling_hungry.png`
- `eggling_hungry_dirty.png`
- `eggling_hungry_poopy.png`
- `eggling_hungry_poopy_dirty.png`
- `eggling_hungry_restless.png`
- `eggling_poopy.png`
- `eggling_poopy_dirty.png`
- `eggling_poopy_restless.png`
- `eggling_restless.png`

### Baby

- `baby_healthy.png`

## Missing Images

### Eggling Still Missing

- `eggling_hungry_poopy_restless.png`
- `eggling_hungry_dirty_restless.png`
- `eggling_poopy_dirty_restless.png`
- `eggling_hungry_poopy_dirty_restless.png`

### Baby Still Missing

- `baby_hungry.png`
- `baby_poopy.png`
- `baby_dirty.png`
- `baby_restless.png`
- `baby_hungry_poopy.png`
- `baby_hungry_dirty.png`
- `baby_hungry_restless.png`
- `baby_poopy_dirty.png`
- `baby_poopy_restless.png`
- `baby_dirty_restless.png`
- `baby_hungry_poopy_dirty.png`
- `baby_hungry_poopy_restless.png`
- `baby_hungry_dirty_restless.png`
- `baby_poopy_dirty_restless.png`
- `baby_hungry_poopy_dirty_restless.png`
- `baby_critical.png`
- `baby_dead.png`

### Child Still Missing

No child images currently exist.

Recommended full set:
- `child_healthy.png`
- `child_hungry.png`
- `child_poopy.png`
- `child_dirty.png`
- `child_restless.png`
- `child_hungry_poopy.png`
- `child_hungry_dirty.png`
- `child_hungry_restless.png`
- `child_poopy_dirty.png`
- `child_poopy_restless.png`
- `child_dirty_restless.png`
- `child_hungry_poopy_dirty.png`
- `child_hungry_poopy_restless.png`
- `child_hungry_dirty_restless.png`
- `child_poopy_dirty_restless.png`
- `child_hungry_poopy_dirty_restless.png`
- `child_critical.png`
- `child_dead.png`

### Teen Still Missing

No teen images currently exist.

Recommended full set:
- `teen_healthy.png`
- `teen_hungry.png`
- `teen_poopy.png`
- `teen_dirty.png`
- `teen_restless.png`
- `teen_hungry_poopy.png`
- `teen_hungry_dirty.png`
- `teen_hungry_restless.png`
- `teen_poopy_dirty.png`
- `teen_poopy_restless.png`
- `teen_dirty_restless.png`
- `teen_hungry_poopy_dirty.png`
- `teen_hungry_poopy_restless.png`
- `teen_hungry_dirty_restless.png`
- `teen_poopy_dirty_restless.png`
- `teen_hungry_poopy_dirty_restless.png`
- `teen_critical.png`
- `teen_dead.png`

### Adult Still Missing

No adult images currently exist.

Recommended full set:
- `adult_healthy.png`
- `adult_hungry.png`
- `adult_poopy.png`
- `adult_dirty.png`
- `adult_restless.png`
- `adult_hungry_poopy.png`
- `adult_hungry_dirty.png`
- `adult_hungry_restless.png`
- `adult_poopy_dirty.png`
- `adult_poopy_restless.png`
- `adult_dirty_restless.png`
- `adult_hungry_poopy_dirty.png`
- `adult_hungry_poopy_restless.png`
- `adult_hungry_dirty_restless.png`
- `adult_poopy_dirty_restless.png`
- `adult_hungry_poopy_dirty_restless.png`
- `adult_critical.png`
- `adult_dead.png`

### Elder Still Missing

No elder images currently exist.

Recommended full set:
- `elder_healthy.png`
- `elder_hungry.png`
- `elder_poopy.png`
- `elder_dirty.png`
- `elder_restless.png`
- `elder_hungry_poopy.png`
- `elder_hungry_dirty.png`
- `elder_hungry_restless.png`
- `elder_poopy_dirty.png`
- `elder_poopy_restless.png`
- `elder_dirty_restless.png`
- `elder_hungry_poopy_dirty.png`
- `elder_hungry_poopy_restless.png`
- `elder_hungry_dirty_restless.png`
- `elder_poopy_dirty_restless.png`
- `elder_hungry_poopy_dirty_restless.png`
- `elder_critical.png`
- `elder_dead.png`

## Shared Action Art Style

Use this prefix for all action/event images:

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages.
```

For action art, prefer the `baby` or `child` version of the pet unless there is a strong reason to depict another stage.

## Action / Event Image Prompts

These are the event-style images the bot can plausibly use in its current feature set.

### `action_spawn.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A newly spawned salamander virtual pet emerging into existence, magical arrival moment, small sparkles around the pet, joyful and fresh, suitable for a new-pet announcement.
```

### `action_feed.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet happily being fed, eager expression, a tiny bowl of food or pellet dish near the pet, warm and cared-for feeling.
```

### `action_scoop.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet looking relieved after cleanup, one or two little cartoon poop piles being tidied away with a tiny scoop nearby, cute and not gross.
```

### `action_play.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet having playtime, bright happy expression, active pose, a simple toy nearby such as a little ball or ribbon, playful energy.
```

### `action_wash.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet being gently washed, clean refreshed expression, a few soap bubbles and a small bath sponge nearby, cute and tidy.
```

### `action_teach_speak.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet learning to speak, curious expression, a stylized speech bubble with abstract symbols instead of words, attentive and teachable mood.
```

### `action_school_start.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet starting school for a new subject, determined expression, tiny book or notebook nearby, exciting first-day-of-school feeling.
```

### `action_school_continue.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet continuing its studies, focused expression, notebook or stack of papers nearby, steady disciplined study mood.
```

### `action_school_upgrade.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet advancing to a higher academic level, proud scholarly expression, a diploma scroll or formal academic paper nearby, celebratory but studious.
```

### `action_school_subjects.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet surrounded by academic symbols, several little books or certificates nearby, thoughtful expression, representing learned subjects and education history.
```

### `action_school_status.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet in the middle of studying, concentrated expression, open book or study materials nearby, representing current learning progress.
```

### `action_graveyard.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but melancholy virtual-pet memorial art for a Telegram bot, centered composition, clean 2D illustration, soft outlines, readable at small size, whimsical but respectful tone. A simple graveyard-themed scene element with a cute cartoon tombstone and a solemn salamander-pet memorial atmosphere, no gore, no text.
```

### `action_commands.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet receiving many quirky instructions, curious expression, surrounded by a few abstract command symbols or little speech bubbles without words, playful and chaotic.
```

### `action_evolve_in.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet anticipating evolution, excited expression, subtle magical glow around the pet, feeling like a countdown to the next life stage.
```

### `action_evolution_baby.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A tiny newly hatched salamander virtual pet at the moment of evolving into the baby stage, celebratory transformation, sparkles, fresh hatching energy, milestone announcement feeling.
```

### `action_evolution_child.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A young salamander virtual pet at the moment of evolving into the child stage, proud and playful transformation, sparkles and growth milestone energy.
```

### `action_evolution_teen.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A lankier salamander virtual pet at the moment of evolving into the teen stage, energetic awkward transformation, sparkles and adolescent growth feeling.
```

### `action_evolution_adult.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A fully formed salamander virtual pet at the moment of evolving into the adult stage, triumphant and confident transformation, sparkles and major milestone energy.
```

### `action_evolution_elder.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. An elder salamander virtual pet at the moment of evolving into the elder stage, wise ancient transformation, subtle magical sparkle, dignified milestone energy.
```

### `action_memorial.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but melancholy virtual-pet memorial art for a Telegram bot, centered composition, clean 2D illustration, soft outlines, readable at small size, respectful but whimsical tone. A tombstone with a small memorial portrait feeling for the salamander virtual pet, peaceful and affectionate, no gore, no text.
```

### `action_memorial_preview.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but melancholy virtual-pet memorial art for a Telegram bot, centered composition, clean 2D illustration, soft outlines, readable at small size, respectful but whimsical tone. A preview-style memorial image for a salamander virtual pet, peaceful and reflective, with a tombstone and gentle memorial mood, no gore, no text.
```

### `action_reset.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet getting a fresh daily reset, relieved and ready-for-the-day expression, subtle circular reset motif or sparkles around it.
```

### `action_rename.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet receiving a new identity, proud pose, a nametag-like symbol without words nearby, ceremonial and cute.
```

### `action_kill.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but melancholy virtual-pet memorial art for a Telegram bot, centered composition, clean 2D illustration, soft outlines, readable at small size, respectful but whimsical tone. A solemn transition image for a salamander virtual pet being forcibly ended by an admin action, peaceful and gentle rather than graphic, memorial mood.
```

### `action_graveyard_remove_last.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet memorial-management art for a Telegram bot, centered composition, clean 2D illustration, soft outlines, readable at small size. A small memorial scene with a salamander-themed tombstone and a gentle undo or rewind feeling, respectful and clean, no text.
```

### `action_stage_art.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A display-style showcase image representing the different life stages of a salamander virtual pet, gallery or showcase mood, no background, no words.
```

### `action_status.png`

```text
Create a PNG-style asset with a fully transparent background. No floor, no shadow plane, no scenery, no environment, no frame, no border, no text. Only the character and any explicitly requested action props should be visible.

Cute but slightly strange virtual-pet creature art for a Telegram bot, centered composition, full body visible, clean 2D illustration, soft outlines, readable at small size, whimsical Tamagotchi-like charm, salamander-inspired creature, consistent design across life stages. A small salamander virtual pet posing for a status check, expressive face, clear readable body language, suitable as a general-purpose status image.
```

## Recommended Next Batch

Highest priority missing assets:

1. Finish the remaining `eggling` combinations.
2. Finish the full `baby` state set.
3. Create `action_feed.png`, `action_scoop.png`, `action_play.png`, `action_wash.png`.
4. Create the school action images.
5. Create memorial and evolution action images.
