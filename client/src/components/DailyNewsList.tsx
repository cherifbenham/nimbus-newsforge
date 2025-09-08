
import React, { useState, useEffect, } from 'react';

import { News, Newsletter } from '../dto/InterfaceDefinition';
import { NewsItem, NewsListTitle, ButtonConfig, SortingConfig } from "./NewsList2";
import ApiHelper from '../backend/ApiHelper';
import { LightBulbIcon, InboxStackIcon } from '@heroicons/react/24/outline';
import axios, { AxiosError } from 'axios';
import useSWR from 'swr'
import config from '../config/apiService';

const serverUrl = config.url.API_URL;





interface DailyNewsListProps {
    start_date: string;
    end_date: string;
    newsletter: Newsletter | null;
    title: string,
    buttons: ButtonConfig[];
}




const DailyNewsList: React.FC<DailyNewsListProps> = ({ newsletter, title, buttons, start_date, end_date }) => {
    const [news, setNews] = useState<News[]>([]);
    const [sortingMode, setSortingMode] = useState("default")


    const fetcher = (url: string) => axios.get(url).then(({ data }) => data.news);

    const params = new URLSearchParams({
        start_date: start_date,
        end_date: end_date,
        ranked: sortingMode === "ranked" ? "true" : "false"
    });

    const { data, error } = useSWR<News[], Error>(`${serverUrl}/news?${params.toString()}`, fetcher, { suspense: true })

    useEffect(() => {
        setNews(processNews(news))

    }, [newsletter]);

    useEffect(() => {
        if (!data) return;
        const news: News[] = data.map(newsItem => ({
            ...newsItem,
            website: extractDomain(newsItem.url), // Extract domain
        }));
        setNews(processNews(news))
    }
        , [data])

    const processNews = (news: News[]) => {
        let newstoprocess = news
        if (sortingMode === "default") {
            newstoprocess = sortNewsByWebsite(news)
        }
        if (newsletter) {
            newstoprocess = tagNewsletterNews(newstoprocess, newsletter)

        }

        return newstoprocess
    }




    const extractDomain = (url: string): string => {
        try {
            const hostname = new URL(url).hostname;
            return hostname.replace(/^www\./i, '');
        } catch (error) {
            return "Unknown (" + url + ")";
        }
    };

    const sortNewsByWebsite = (newsList: News[]): News[] => {
        return [...newsList].sort((a, b) => a.website.localeCompare(b.website));
    }

    const tagNewsletterNews = (newsList: News[], newsletter: Newsletter | null): News[] => {
        if (!newsletter || !newsletter.sections) return newsList;

        const newsletterUrls = new Set<string>();

        const addUrlsToSet = (newsItems: News[]) => newsItems.forEach(item => newsletterUrls.add(item.url));

        addUrlsToSet(newsletter.sections?.topNews || []);
        addUrlsToSet(newsletter.sections?.podcasts || []);
        addUrlsToSet(newsletter.sections?.moreStories || []);

        (newsletter.sections.regionalNews || []).forEach(regionalSection =>
            regionalSection.news.forEach(item => newsletterUrls.add(item.url))
        );

        return newsList.map(newsItem => ({ ...newsItem, is_in_newsletter: newsletterUrls.has(newsItem.url) }));
    };



    const sortConfig: SortingConfig = {
        current_value: sortingMode,
        callback: (option) => setSortingMode(option),
        options: [
            {
                icon: <InboxStackIcon className="h-5 w-5 " />,
                title: 'Default',
                option_key: 'default',
            },
            {
                icon: <LightBulbIcon className="h-5 w-5 " />,
                title: 'Ranked Sort',
                option_key: 'ranked',
            },
        ]
    }

    return (
        <div>

            <div className="flex flex-col overflow-y-auto p-4 rounded-lg">
                <NewsListTitle title={title} sortConfig={sortConfig} />
                <div className="max-h-[700px] overflow-y-auto">
                    {news.map((item, index) => (
                        <NewsItem key={index} news={item} buttons={buttons} />
                    ))}
                </div>
            </div>



        </div>
    );
};

export default DailyNewsList;