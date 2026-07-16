// Mock data for the Creative page.

import type { CreativeProject, StoryBible } from '@/types/creative';

const lighthouseBible: StoryBible = {
  characters: [
    {
      uuid: 'ch-ll-001',
      name: 'Mira Vellan',
      role: 'protagonist',
      description:
        'The last keeper of the Cape Aldwych lighthouse, 64. Stubborn, observant, privately afraid of silence.',
      relations: [
        { target: 'ch-ll-002', relation: 'former lover' },
        { target: 'ch-ll-003', relation: 'mother' },
      ],
    },
    {
      uuid: 'ch-ll-002',
      name: 'Hannes Vellan',
      role: 'deuteragonist',
      description:
        'Mira\'s estranged ex-husband. A marine biologist who left the cape for a research post in Reykjavik.',
      relations: [{ target: 'ch-ll-001', relation: 'ex-husband' }],
    },
    {
      uuid: 'ch-ll-003',
      name: 'Solveig Vellan',
      role: 'supporting',
      description:
        'Mira\'s late mother. Wrote a series of unsent letters that surface at the start of act two.',
      relations: [{ target: 'ch-ll-001', relation: 'daughter' }],
    },
  ],
  worldview: `# The World of Cape Aldwych

Cape Aldwych is a fictional headland on the western edge of Iceland. The story is set in **2049**, six years after the last automated lighthouse was commissioned in the region.

## The Keepers

The Vellan family has tended the Cape Aldwych light for **four generations**. The role is a hereditary duty, but also a quiet form of exile: keepers rarely leave the cape for more than a fortnight at a time.

## The Silence

When the novel opens, a *new* silence has fallen. Birds that once nested on the cliffs have stopped arriving. Marine traffic has thinned. Mira is the only person who seems to notice.

## Tone

- Literary sci-fi
- First person, present tense
- Sparse dialogue, long interior passages
- A single supernatural event in act three, otherwise realist
`,
  chapters: [
    {
      uuid: 'ch-lighthouse-01',
      chapter_title: 'The Light That Is Not Lit',
      word_count: 4200,
      content:
        'Mira climbed the spiral staircase at 04:11, as she had every morning for thirty-eight years. The light was no longer lit. The lamp had not been needed since the automation, but the climb itself was the ritual. Up there, the world shrank to a square of salt and sky.',
    },
    {
      uuid: 'ch-lighthouse-02',
      chapter_title: 'A Letter in a Coffee Tin',
      word_count: 5100,
      content:
        'Solveig\'s letters were kept in a coffee tin behind the spare blankets. Mira had known about them for years and never opened the lid. On the morning of the storm, she finally did.',
    },
    {
      uuid: 'ch-lighthouse-03',
      chapter_title: 'The Thing That Came Ashore',
      word_count: 6300,
      content:
        'It was not a whale. It was not a wreck. It was, Mira decided later, a question the ocean had been asking her for twenty years, and which she had refused, very politely, to answer.',
    },
    {
      uuid: 'ch-lighthouse-04',
      chapter_title: 'Reykjavik',
      word_count: 4800,
      content:
        'Hannes met her at the arrivals gate holding a paper sign that said VELLAN in his careful handwriting. They did not embrace. They walked, side by side, to the car park.',
    },
  ],
};

const carbonBible: StoryBible = {
  characters: [
    {
      uuid: 'ch-cb-001',
      name: 'Dr. Iyana Okafor',
      role: 'protagonist',
      description:
        'A geochemist whose grandmother worked the Nigerian coalfields. Narrator, 41, restless, allergic to oversimplification.',
      relations: [
        { target: 'ch-cb-002', relation: 'advisor' },
        { target: 'ch-cb-003', relation: 'former student' },
      ],
    },
    {
      uuid: 'ch-cb-002',
      name: 'Prof. Halldór Einarsson',
      role: 'mentor',
      description:
        'Iyana\'s PhD advisor. A climate modeller with a soft voice and a sharp memory for the 1970s energy crisis.',
      relations: [{ target: 'ch-cb-001', relation: 'student' }],
    },
    {
      uuid: 'ch-cb-003',
      name: 'Mei Tanaka',
      role: 'supporting',
      description:
        'Iyana\'s former student, now an investigative journalist. Pushes Iyana out of her academic comfort zone.',
      relations: [{ target: 'ch-cb-001', relation: 'former advisor' }],
    },
  ],
  worldview: `# A Brief History of Carbon

A non-fiction narrative about **carbon** as a chemical, an economic unit, and a moral category.

## Scope

Three threads weave through the book:

1. **The chemistry** — how a single element binds into fuels, plastics, and life itself.
2. **The economics** — how the coal, oil, and gas industries built and continue to shape the modern world.
3. **The ethics** — what we owe to the people who lived through the carbon century, and the people who will live after it.

## Voice

- Essayistic, in the tradition of John McPhee and Robert Macfarlane
- 12 short chapters, each anchored to a single place
- Footnotes carry the technical load; the prose carries the moral weight
`,
  chapters: [
    {
      uuid: 'ch-carbon-01',
      chapter_title: 'A Lump of Coal in the Hand',
      word_count: 3400,
      content:
        'There is a particular weight to a lump of anthracite — dense, almost cool to the touch, and faintly soapy along its cleavage planes. Hold one for a minute and you begin to understand why an entire civilization decided it was worth digging up.',
    },
    {
      uuid: 'ch-carbon-02',
      chapter_title: 'The Plastic Century',
      word_count: 4100,
      content:
        'Bakelite was a miracle that escaped the laboratory. Celluloid was a miracle that ate the nitrate film industry alive. The lesson, again and again, is the same: polymerise carbon, and you change the world — usually in two directions at once.',
    },
    {
      uuid: 'ch-carbon-03',
      chapter_title: 'The Sinking Archipelago',
      word_count: 5200,
      content:
        'Iyana visits Tuvalu for the first time. The runway is already, by any honest measurement, an act of geological defiance.',
    },
  ],
};

const staticBible: StoryBible = {
  characters: [
    {
      uuid: 'ch-st-001',
      name: 'Joon Park',
      role: 'protagonist',
      description:
        'A 22-year-old archivist in a future Seoul where memories can be backed up, edited, and resold.',
      relations: [{ target: 'ch-st-002', relation: 'client' }],
    },
    {
      uuid: 'ch-st-002',
      name: 'The Customer',
      role: 'antagonist',
      description:
        'Never named. Identifiable only by the colour of their coat and the way they never blink.',
      relations: [{ target: 'ch-st-001', relation: 'archivist' }],
    },
  ],
  worldview: `# Garden of Static

A **noir cyberpunk** novella-in-progress. The book is paused after chapter three while the author researches Seoul housing policy.

## Setting

Near-future Seoul. The han river is half-covered by data centres. Memory editing is legal but taxed. Archiving is a licensed profession, much like notary work in the 20th century.

## Aesthetic

- Rain-slick neon, but no flying cars
- Hand-typed code; no AI assistance
- Loneliness that is structural, not sentimental
`,
  chapters: [
    {
      uuid: 'ch-static-01',
      chapter_title: 'The Archivist Opens',
      word_count: 2900,
      content:
        'Joon arrives at the shop at 06:50, ten minutes before opening. The door still uses a physical key. He has told the landlord three times that this is a fire hazard; the landlord has told him, three times, that fire is good for the character of a building.',
    },
    {
      uuid: 'ch-static-02',
      chapter_title: 'A Coat the Colour of Rain',
      word_count: 3500,
      content:
        'The customer arrived at 14:07. They did not say hello. They said: "I would like a copy of last Tuesday, between 19:42 and 20:15."',
    },
  ],
};

export const creativeProjects: CreativeProject[] = [
  {
    uuid: 'cp-001',
    title: 'The Last Lighthouse Keeper',
    status: 'active',
    word_count: 32450,
    created_at: '2025-11-04 10:00:00',
    updated_at: '2026-07-12 22:01:00',
    story_bible: lighthouseBible,
  },
  {
    uuid: 'cp-002',
    title: 'A Brief History of Carbon',
    status: 'completed',
    word_count: 18200,
    created_at: '2025-08-21 09:30:00',
    updated_at: '2026-05-20 14:42:00',
    story_bible: carbonBible,
  },
  {
    uuid: 'cp-003',
    title: 'Garden of Static',
    status: 'paused',
    word_count: 7820,
    created_at: '2026-02-12 18:11:00',
    updated_at: '2026-04-02 09:15:00',
    story_bible: staticBible,
  },
];

export const getProjectByUuid = (uuid: string): CreativeProject | undefined =>
  creativeProjects.find((p) => p.uuid === uuid);
