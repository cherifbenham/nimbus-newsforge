import { z } from 'zod'
import { DateTime } from 'luxon'




export const NewsletterHeaderSchema = z.object({
    id: z.string(),
    publishDate: z.date(),
})

export type NewsletterHeader = z.infer<typeof NewsletterHeaderSchema>


export const NewsSchema = z.object({
    url: z.string(),
    title: z.string(),
    abstract: z.string().nullish(),
    website: z.string(),
    ref: z.number().optional(),
    publishDate: z.date().optional(),
    gen_key_message: z.string().optional(),
    gen_context: z.string().optional(),
    is_in_newsletter: z.boolean().optional()

})

export type News = z.infer<typeof NewsSchema>

export const SelectedNewsSchema = z.object({
    NewsSchema,
    reason: z.string().optional(),
    duplicate_candidates: z.array(NewsSchema).optional(),
})

export type SelectedNews = z.infer<typeof SelectedNewsSchema>

const NewsletterRegionSectionSchema = z.object({
    region: z.string(),
    news: z.array(NewsSchema),
})

export type NewsletterRegionSection = z.infer<typeof NewsletterRegionSectionSchema>


const NewsletterSectionsSchema = z.object({
    topNews: z.array(NewsSchema).optional(),
    podcasts: z.array(NewsSchema).optional(),
    regionalNews: z.array(NewsletterRegionSectionSchema).optional(),
    moreStories: z.array(NewsSchema).optional(),
})

export type NewsletterSections = z.infer<typeof NewsletterSectionsSchema>


export const NewsletterSchema = z.object({
    start_date: z.string().transform((str) => DateTime.fromISO(str).toJSDate()),
    end_date: z.string().transform((str) => DateTime.fromISO(str).toJSDate()),
    sections: NewsletterSectionsSchema,

})

export type Newsletter = z.infer<typeof NewsletterSchema>


const DigestSubSectionSchema = z.object({
    name: z.string(),
    news: z.array(NewsSchema),
})

export type DigestSubSection = z.infer<typeof DigestSubSectionSchema>


const DigestSectionSchema = z.object({
    name: z.string(),
    subSections: z.array(DigestSubSectionSchema).optional(),
    news: z.array(NewsSchema).optional(),
})

export type DigestSection = z.infer<typeof DigestSectionSchema>

export const DigestHighlightNews = z.object({
    url: z.string(),
    title: z.string(),
    abstract: z.string().nullish().optional(),
    ref: z.number(),
    website: z.string(),
})

export const DigestHightlightSchema = z.object({
    text: z.string(),
    markdown_text: z.string(),
    news: z.array(DigestHighlightNews),
})

export type DigestHighlight = z.infer<typeof DigestHightlightSchema>




export const DigestSchema = z.object({
    start_date: z.coerce.date(),
    end_date: z.coerce.date(),
    highlight: DigestHightlightSchema,
    sections: z.array(DigestSectionSchema),
})

export type Digest = z.infer<typeof DigestSchema>




export const SearchRequestSchema = z.object({
    query: z.string().min(1, 'Search query must be at least 1 character long'),
    page: z.string().transform(Number).optional(),
});
export type SearchRequest = z.infer<typeof SearchRequestSchema>;



export const SearchResultSchema = z.object({
    title: z.string(),
    type: z.string(),
    url: z.string().optional(),
    snippet: z.string().optional(),
});
export const SearchResponseSchema = z.object({
    totalsize: z.number(),
    nextpagetoken: z.string().optional(),
    summary: z.string().optional(),
    results: NewsSchema.array(),
})

export type SearchResult = z.infer<typeof SearchResultSchema>;
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

export const ComposeWeeklyClasses = [
    "General Industry News",
    "Competitors",
    "M&A & Investments",
    "Travel Providers",
    "Financial Reports / Info",
    "Research & Reports",
] as const;

export const ComposeWeeklyItemSchema = z.object({
    id: z.string(),
    title: z.string(),
    abstract: z.string().optional(),
    url: z.string().optional(),
    date: z.string().optional(),
    class_daily: z.string().optional(),
});

export type ComposeWeeklyItem = z.infer<typeof ComposeWeeklyItemSchema>;

export const ComposeWeeklyInsightSchema = z.object({
    id: z.string(),
    refined_title: z.string().optional(),
    gemini_comment: z.string(),
    gemini_classification: z.string(),
    similarity: z.number().int().min(0).max(100).optional(),
});

export type ComposeWeeklyInsight = z.infer<typeof ComposeWeeklyInsightSchema>;
