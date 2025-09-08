import { DateTime } from 'luxon';
import { Digest } from "../dto/InterfaceDefinition"

const syntheticDigest: Digest = {
    start_date: DateTime.fromObject({ year: 2024, month: 9, day: 23 }).toJSDate(),
    end_date: DateTime.fromObject({ year: 2024, month: 9, day: 26 }).toJSDate(),
    highlight: {
        text: 'Highlight text',
        markdown_text: 'Highlight markdown',
        news: [
            {
                url: 'highlight-url-1',
                title: 'Highlight Title 1',
                ref: 1,
                abstract: 'Industry Reg Abstract 1',
                website: 'website.com',
            },
        ],
    },
    sections: [
        {
            name: 'Industry / Regulation',
            subSections: [
                {
                    name: 'SubSection 1',
                    news: [
                        {
                            url: 'industry-reg-url-1',
                            title: 'Industry Reg Title 1',
                            abstract: 'Industry Reg Abstract 1',
                            website: 'website.com',
                        },
                    ],
                },
            ],
        },
        {
            name: 'Competitors',
            subSections: [
                {
                    name: 'Sabre',
                    news: [
                        {
                            url: 'sabre-url-1',
                            title: 'Sabre Title 1',
                            abstract: 'Sabre Abstract 1',
                            website: 'sabre.com',
                        },
                    ],
                },
                {
                    name: 'Google',
                    news: [
                        {
                            url: 'google-url-1',
                            title: 'Google Title 1',
                            abstract: 'Google Abstract 1',
                            website: 'google.com',
                        },
                    ],
                },
            ],
            news: [], //Example of an empty news array.
        },
        // Add more sections as needed...
    ],
};

//Example of exporting the data for use in tests
export default syntheticDigest;