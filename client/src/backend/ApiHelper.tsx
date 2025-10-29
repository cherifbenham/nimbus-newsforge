import axios from 'axios';
import config from '../config/apiService';
import { Digest, DigestHighlight, NewsletterHeader, Newsletter, NewsletterSchema, News, NewsSchema, SearchResponseSchema, SearchResponse, DigestSchema, DigestHightlightSchema, ComposeWeeklyItem, ComposeWeeklyInsightSchema, ComposeWeeklyInsight } from '../dto/InterfaceDefinition';
import { z } from 'zod';



const serverUrl = config.url.API_URL;

interface HistoryResponse {
    id: string;
    start_date: string;
    end_date: string;
}

interface NewsletterSaveResponse {
    id: string;
}




export const ApiHelper = {
    async getNewsletterHistory(): Promise<NewsletterHeader[]> {

        try {

            const response = await axios.get(`${serverUrl}/newsletters`);
            const formattedResponse = response.data.map(((item: HistoryResponse) => ({
                id: item.id,
                publishDate: new Date(item.end_date),
            })));

            return formattedResponse
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    },

    async getDigestHistory(): Promise<NewsletterHeader[]> {

        try {

            const response = await axios.get(`${serverUrl}/digests`);
            const formattedResponse = response.data.map(((item: HistoryResponse) => ({
                id: item.id,
                publishDate: new Date(item.start_date),
            })));

            return formattedResponse
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    },

    async getNewsletter(nlId: string): Promise<Newsletter> {
        try {
            const response = await axios.get(`${serverUrl}/newsletter/id?id=${nlId}`);
            const data = response.data;

            // Parse the data using the Zod schema.  This will throw an error if the data doesn't match the schema.
            const parsedNewsletter = NewsletterSchema.parse(data);

            return parsedNewsletter;
        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid newsletter data received from server.');
            } else {
                console.error('Error fetching newsletter:', error);
                throw error; // Re-throw other errors
            }
        }
    }
    ,
    async analyzeComposeWeekly(items: ComposeWeeklyItem[]): Promise<ComposeWeeklyInsight[]> {
        try {
            const response = await axios.post(`${serverUrl}/compose-weekly/analyze`, { items });
            const parsed = ComposeWeeklyInsightSchema.array().parse(response.data.results);
            return parsed;
        } catch (error) {
            console.error('Error analyzing compose weekly items:', error);
            throw error;
        }
    },
    async composeEmailFromNewsletter(newsletter: Newsletter, subjectHint?: string): Promise<{ subject: string, html: string }> {
        const payload: any = { newsletter };
        if (subjectHint) payload.subject_hint = subjectHint;
        const response = await axios.post(`${serverUrl}/newsletters/email/compose`, payload);
        return response.data as { subject: string, html: string };
    },
    async composeCuratedEmailFromNewsletter(newsletter: Newsletter, subjectHint?: string, maxItems: number = 5): Promise<{ subject: string, html: string }> {
        const payload: any = { newsletter, max_items: maxItems };
        if (subjectHint) payload.subject_hint = subjectHint;
        const response = await axios.post(`${serverUrl}/newsletters/email/compose/curated`, payload);
        return response.data as { subject: string, html: string };
    },
    async getNewsForPeriod(startDate: Date, endDate: Date, website?: string, ranked?: boolean): Promise<News[]> {
        try {
            const params = {
                start_date: startDate.toISOString(),
                end_date: endDate.toISOString(),
                website: website,
                ranked: ranked || false
            } as any;
            if (website) {
                params.website = website;
            }
            const response = await axios.get(`${serverUrl}/news`, { params });

            if (response.data.news) {
                return response.data.news;
            } else {
                console.error("Error: News data not found in response:", response.data);
                return [];
            }


        } catch (error) {
            console.error('Error fetching news:', error);
            throw error;
        }
    },

    async analyzeNews(news: News): Promise<string> {
        try {
            const response = await axios.post(`${serverUrl}/news/analyze`, { news });
            return response.data;
        } catch (error) {
            console.error("Error analyzing news");
        }

        return "";
    },

    async generateNewsletter(startDate: Date, endDate: Date): Promise<Newsletter> {
        try {
            const response = await axios.post(`${serverUrl}/newsletters/generate`, { start_date: startDate.toISOString(), end_date: endDate.toISOString() });

            const data = response.data;

            // Parse the data using the Zod schema.  This will throw an error if the data doesn't match the schema.
            const parsedNewsletter = NewsletterSchema.parse(data);

            return parsedNewsletter;
        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid newsletter data received from server.');
            } else {
                console.error('Error fetching newsletter:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async saveNewsletter(newsletter: Newsletter, id?: string): Promise<string> {
        try {
            let data: NewsletterSaveResponse;
            if (id) {
                // Update existing newsletter
                const response = await axios.put(`${serverUrl}/newsletters/${id}`, { newsletter });
                data = response.data;
            } else {
                // Create new newsletter
                const response = await axios.post(`${serverUrl}/newsletters`, { newsletter });
                data = response.data;
            }
            return data.id;
        } catch (error) {
            console.error('Error saving newsletter:', error);
            throw error; // Re-throw the error to be handled by the caller
        }
    },  

    async deleteNewsletter(nlId: string): Promise<void> {
        try {
            await axios.delete(`${serverUrl}/newsletters/${nlId}`);
            console.log("Successfully deleted. Id:" + nlId)


        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid newsletter data received from server.');
            } else {
                console.error('Error deleting newsletter:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async getNewsForDigest(startDate: Date): Promise<News[]> {
        try {
            const response = await axios.get(`${serverUrl}/digest/news?start_date=${startDate.toISOString()}`);
            const data = response.data;
            const parsedList = NewsSchema.array().parse(data);

            return parsedList;
        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid news data received from server.');
            } else {
                console.error('Error fetching news list:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async getDigest(digestId: string): Promise<Digest> {
        try {
            const response = await axios.get(`${serverUrl}/digests/id?id=${digestId}`);
            const data = response.data;
            const parsedDigest = DigestSchema.parse(data);
            return parsedDigest
        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid digest data received from server.');
            } else {
                console.error('Error fetching digest:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async generateDigest(startDate: Date): Promise<Digest> {
        try {
            const endDate = new Date(startDate.getTime() + 7 * 24 * 60 * 60 * 1000); // Add 7 days to the start date


            const response = await axios.post(`${serverUrl}/digests/generate`, { start_date: startDate.toISOString(), end_date: endDate.toISOString() });

            const data = response.data;

            // Parse the data using the Zod schema.  This will throw an error if the data doesn't match the schema.
            const parsedDigest = DigestSchema.parse(data);

            return parsedDigest;
        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid digest data received from server.');
            } else {
                console.error('Error fetching digest:');
                if (error instanceof axios.AxiosError) {
                    if (error.response?.data) {
                        console.log(error.response?.data)
                    }
                } else {
                    console.log(error)
                }
            }
            throw error
        }
    },

    async generateDigestHighlight(digest: Digest): Promise<DigestHighlight> {
        try {


            const response = await axios.post(`${serverUrl}/digests/highlight/generate`, { digest: digest });

            const data = response.data;
            console.log(data)

            // Parse the data using the Zod schema.  This will throw an error if the data doesn't match the schema.
            const parsedDigest = DigestHightlightSchema.parse(data);
            console.log(parsedDigest)

            return parsedDigest;
        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid digest data received from server.');
            } else {
                console.error('Error generating Highlight:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async saveDigest(digest: Digest, digestId?: string): Promise<string> {
        try {
            let data;
            if (digestId) {
                // Update existing digest
                const response = await axios.put(`${serverUrl}/digests/${digestId}`, { digest });
                data = response.data;
            } else {
                // Create new digest requires digest + start/end dates
                const response = await axios.post(`${serverUrl}/digests`, {
                    digest: digest,
                    start_date: digest.start_date instanceof Date ? digest.start_date.toISOString() : digest.start_date,
                    end_date: digest.end_date instanceof Date ? digest.end_date.toISOString() : digest.end_date,
                });
                data = response.data;
            }
            return data.id;

        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid newsletter data received from server.');
            } else {
                console.error('Error saving newsletter:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async deleteDigest(nlId: string): Promise<void> {
        try {
            await axios.delete(`${serverUrl}/digests/${nlId}`);
            console.log("Successfully deleted. Id:" + nlId)


        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid newsletter data received from server.');
            } else {
                console.error('Error deleting newsletter:', error);
                throw error; // Re-throw other errors
            }
        }
    },

    async searchNews(query: string): Promise<SearchResponse> {
        try {
            const response = await axios.get(`${serverUrl}/news/search`, { params: { input: query } });
            const parsedSearchResults = SearchResponseSchema.parse(response.data);
            console.log(parsedSearchResults)


            return parsedSearchResults


        } catch (error) {
            if (error instanceof z.ZodError) {
                // Handle Zod validation errors specifically.  Log the error for debugging.
                console.error('Validation error:', error.issues);
                // You might choose to throw a custom error here, or re-throw the ZodError.
                throw new Error('Invalid newsletter data received from server.');
            } else {
                console.error('Error searching news', error);
                throw error; // Re-throw other errors
            }
        }
    }




}

export default ApiHelper
