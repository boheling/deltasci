// Maps a deltasci KnowledgeGap category into the four human-in-the-loop sections
// (why-flagged, fair concern, expert prompt) that the KnowledgeGapPanel renders.
//
// This is the "judge's reasoning" analog from biointel's ReproductionScoreboard,
// but instead of an LLM judge it's a deterministic mapping from the AI's
// self-declared epistemic category.

import type { GapCategory } from './types';

export interface CategoryGuidance {
  whyFlagged: string;
  fairConcern: string;
  expertPrompt: string;
  expertPersona: string; // who is the right human to bring in
}

const FALLBACK: CategoryGuidance = {
  whyFlagged:
    'The AI explicitly chose not to fabricate a citation here. The claim sits outside the part of the literature it is confident about.',
  fairConcern:
    'Could be a gap in the AI\'s training corpus rather than a true unknown. Worth checking whether recent or paywalled work covers it.',
  expertPrompt: 'What is the current evidence on this question that the AI may have missed?',
  expertPersona: 'a domain expert with current literature exposure',
};

const MAP: Record<GapCategory, CategoryGuidance> = {
  'lab-tribal-knowledge': {
    whyFlagged:
      'This is the kind of context that lives in lab notebooks, slack threads, and protocols — not in publications the AI was trained on.',
    fairConcern:
      'Almost certainly a true gap (not a corpus shortfall). The AI cannot know what the lab knows internally.',
    expertPrompt:
      'What protocol, definition, or operational detail does the lab actually use here, and is it documented anywhere?',
    expertPersona: 'the PI or a senior member of the originating lab',
  },
  'paywalled-or-non-OA': {
    whyFlagged:
      'Relevant evidence likely exists in publications the AI was not trained on (paywalled journals, society proceedings, dissertations).',
    fairConcern:
      'Possibly resolvable by a literature search the AI cannot perform. Not necessarily a true unknown.',
    expertPrompt:
      'Is there published evidence on this in a paywalled or non-open-access source that should be pulled?',
    expertPersona: 'a librarian or domain expert with full-text access',
  },
  'non-english-literature': {
    whyFlagged:
      'Relevant work has likely been published in non-English literature (Japanese, Chinese, Korean, German, French clinical journals) the AI has weaker coverage on.',
    fairConcern:
      'Possibly a corpus gap rather than a true unknown — but real for any researcher relying on English-only review.',
    expertPrompt:
      'Are there non-English-language publications on this topic that change the picture, and what do they say?',
    expertPersona: 'a domain expert with reading fluency in the relevant non-English literature',
  },
  'niche-subfield': {
    whyFlagged:
      'The AI flagged this as a subfield where it has thin training coverage. It might know the broad strokes but not the field-specific detail.',
    fairConcern:
      'Could be either a true frontier gap or an under-trained niche. Specialist confirmation is the cheapest way to find out.',
    expertPrompt:
      'Is there active work in this subfield that the AI missed, and how does it change the design?',
    expertPersona: 'a specialist in the subfield being flagged',
  },
  'unpublished-or-pilot-data': {
    whyFlagged:
      'The relevant data point exists in the researcher\'s pilot, IRB application, or institutional dataset — not in any external publication.',
    fairConcern:
      'A true unknown to the AI. Pilot data is exactly the input that turns a defensible prior into a data-anchored hypothesis.',
    expertPrompt:
      'What does the pilot or institutional dataset actually show, and does it support or contradict the AI\'s assumed effect size?',
    expertPersona: 'the researcher or an analyst with pilot-data access',
  },
  'patent-or-clinical-practice': {
    whyFlagged:
      'Relevant guidance lives in patents, clinical practice guidelines, regulatory filings, or trial protocols — not always indexed in the AI\'s training literature.',
    fairConcern:
      'Often a corpus gap. The AI may know the science but not the operational standard the field actually uses.',
    expertPrompt:
      'What does the current clinical practice guideline, trial protocol, or regulatory standard say here?',
    expertPersona: 'a clinician, regulatory specialist, or trial methodologist',
  },
  'novel-cross-disciplinary-connection': {
    whyFlagged:
      'The AI flagged this as a connection across disciplines that has not (to its knowledge) been explicitly written down.',
    fairConcern:
      'Possibly a real novel synthesis worth pursuing. Possibly an idea published in a corner of the literature the AI didn\'t survey.',
    expertPrompt:
      'Has anyone connected these two areas before, and is the proposed cross-disciplinary leap defensible?',
    expertPersona: 'a researcher who works at the intersection of the two disciplines',
  },
  other: FALLBACK,
};

export function categoryGuidance(category: string): CategoryGuidance {
  if (category in MAP) {
    return MAP[category as GapCategory];
  }
  return FALLBACK;
}
