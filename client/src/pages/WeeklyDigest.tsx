import React, { useState, useRef, useEffect, useCallback, useContext } from 'react';
import { NewsletterContext, NewsletterContextType } from "../context/NewsletterContext";
import flatpickr from "flatpickr";
import NewsList, { ButtonConfig } from '../components/NewsList2';
import { News, Digest, DigestHighlight } from '../dto/InterfaceDefinition';
import ApiHelper from '../backend/ApiHelper';
import NewsListSkeleton from '../components/skeletons/NewsListSkeleton';
import NewsletterRendererSkeleton from '../components/skeletons/NewsletterSkeleton';
import DigestRenderer from '../components/DigestRenderer';
import { RectangleGroupIcon, SparklesIcon, XCircleIcon, CalendarIcon } from '@heroicons/react/24/outline';

interface WeeklyDigestProps { }


const WeeklyDigest: React.FC<WeeklyDigestProps> = () => {
    const [startDate, setStartDate] = useState<string | null>(null);
    const [news, setNews] = useState<News[]>([]);
    const [digest, setDigest] = useState<Digest | null>(null);
    const { digestId, setIsNewDigest, isNewDigest } = useContext(NewsletterContext) as NewsletterContextType;
    const [newsIsLoading, setNewsIsLoading] = useState(false)
    const [newsletterIsLoading, setNewsletterIsLoading] = useState(false)

    const startDateRef = useRef<HTMLInputElement>(null);

    //=========================
    // Load News Data
    //==========================
    useEffect(() => {
        if (!digest || !digest.start_date) return;
        loadNews(digest?.start_date);

    }, [digest?.start_date]);


    const loadNews = async (news_start: Date) => {
        if (news_start) {
            setNewsIsLoading(true);
            try {
                const newsData = await ApiHelper.getNewsForDigest(news_start);
                const taggedNews = tagDigestNews(newsData, digest)
                setNews(taggedNews);
            } catch (error) {
                console.error('Error fetching news:', error);
            }

            setNewsIsLoading(false);
        }
    }

    useEffect(() => {
        if (isNewDigest) {
            setDigest(null);
            setNews([]);
        }
    }, [isNewDigest])

    useEffect(() => {
        const loaDigest = async () => {
            if (!digestId) return;
            const digestData = await ApiHelper.getDigest(digestId);
            if (digestData) {
                setDigest(digestData);
            }
        };
        setNewsletterIsLoading(true);
        loaDigest();
        if (digest?.start_date) {
            console.log("Loading News")
            console.log(digest.start_date)
            loadNews(digest.start_date)
        }

        setNewsletterIsLoading(false);

    }, [digestId]);

    useEffect(() => {
        const updateTaggedNews = () => {
            const taggedNews = tagDigestNews(news, digest)
            setNews(taggedNews)
        };
        updateTaggedNews()

    }, [digest]);

    const tagDigestNews = (newsList: News[], digest: Digest | null): News[] => {
        if (!digest || !digest.sections) return newsList;

        const digestUrls = new Set<string>();

        const addUrlsToSet = (newsItems: News[]) => newsItems.forEach(item => digestUrls.add(item.url));

        digest.sections.map(section => {
            if (section.news) {
                addUrlsToSet(section.news)
            }
            if (section.subSections) {
                section.subSections.map(subsection => {
                    if (subsection.news) {
                        addUrlsToSet(subsection.news)
                    }
                })
            }
        });



        return newsList.map(newsItem => ({ ...newsItem, is_in_newsletter: digestUrls.has(newsItem.url) }));
    };

    const handleGenerate = async () => {
        if (startDate) {
            const startDateObj = new Date(startDate.toString());
            setNewsletterIsLoading(true);
            const digestData = await ApiHelper.generateDigest(startDateObj);
            setDigest(digestData);
            setIsNewDigest(false)
            setNewsletterIsLoading(false);

        }

    }


    const initializeFlatpickr = useCallback((ref: any, setState: any) => {
        if (ref.current) {
            const fp = flatpickr(ref.current, {
                enableTime: true,
                dateFormat: "Y-m-d H:i",
                onChange: (selectedDates, dateStr, instance) => {
                    const date = new Date(dateStr);
                    setState(date);
                },
            });
            return () => fp.destroy();
        }
        return () => { };
    }, []);

    useEffect(() => {
        if (isNewDigest) {
            // Initialize Flatpickr only when the input elements are rendered
            const cleanupStartDate = initializeFlatpickr(startDateRef, setStartDate);
            return () => {
                cleanupStartDate();
            };
        }
    }, [isNewDigest, initializeFlatpickr, setStartDate]);

    const handleMoveToSection = (newsItem: News, targetSection: string) => {
        const updatedDigest = { ...digest };

        if (!updatedDigest || !updatedDigest.sections) return;

        // Find and remove the news item
        const updatedSections = updatedDigest.sections.map(section => {
            const updatedSection = { ...section };
            if (updatedSection.news) {
                updatedSection.news = updatedSection.news.filter(item => item.url !== newsItem.url);
            }
            if (updatedSection.subSections) {
                updatedSection.subSections = updatedSection.subSections.map(subsection => ({
                    ...subsection,
                    news: subsection.news.filter(item => item.url !== newsItem.url)
                }));
            }
            return updatedSection;
        });


        // Add to target section
        const targetSectionIndex = updatedSections.findIndex(section => section.name === targetSection);
        if (targetSectionIndex !== -1) {
            const updatedTargetSection = { ...updatedSections[targetSectionIndex] };
            updatedTargetSection.news = [...(updatedTargetSection.news || []), newsItem];
            updatedSections[targetSectionIndex] = updatedTargetSection;
        }

        setDigest({ ...updatedDigest, sections: updatedSections } as Digest);


    };

    const handleAddToHighlights = (newsItem: News) => {
        const updatedDigest = { ...digest };

        if (!updatedDigest || !updatedDigest.sections || !updatedDigest.highlight) return;



        // Add to highlights
        const updatedHighlight = { ...updatedDigest.highlight };
        updatedHighlight.news = [...updatedHighlight.news, newsItem] as DigestHighlight["news"];

        setDigest({ ...updatedDigest, highlight: updatedHighlight } as Digest);
    };

    const handleDeleteFromDigest = (newsItem: News) => {
        const updatedDigest = { ...digest };

        if (!updatedDigest || !updatedDigest.sections) return;

        // Find and remove the news item from all sections and subsections
        const updatedSections = updatedDigest.sections.map(section => {
            const updatedSection = { ...section };
            if (updatedSection.news) {
                updatedSection.news = updatedSection.news.filter(item => item.url !== newsItem.url);
            }
            if (updatedSection.subSections) {
                updatedSection.subSections = updatedSection.subSections.map(subsection => ({
                    ...subsection,
                    news: subsection.news.filter(item => item.url !== newsItem.url)
                }));
            }
            return updatedSection;
        });

        setDigest({ ...updatedDigest, sections: updatedSections } as Digest);
    };

    const handleDeleteFromHighlights = (newsItem: News) => {
        const updatedDigest = { ...digest } as Digest;

        if (!updatedDigest || !updatedDigest.highlight) return;

        updatedDigest.highlight.news = updatedDigest.highlight.news.filter(item => item.url !== newsItem.url);

        setDigest({ ...updatedDigest } as Digest);
    };

    const newsListButtonsConfig: ButtonConfig[] = [
        {
            icon: <RectangleGroupIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Move to Another section',
            options: {
                dropdownItems:
                    digest?.sections.map((region) => (
                        { label: region.name, onClick: (newsItem) => handleMoveToSection(newsItem, region.name) }
                    )) || []

            }
        }
    ]

    const hightlightButtons: ButtonConfig[] = [
        {
            icon: <XCircleIcon className="h-5 w-5 text-red-500 hover:text-red-700" />,
            title: 'Remove from Digest',
            options: {
                onClick: (newsItem) => handleDeleteFromHighlights(newsItem),
            }
        }
    ]

    const rendererButtonsConfig: ButtonConfig[] = [
        {
            icon: <RectangleGroupIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Move to Another section',
            options: {
                dropdownItems:
                    digest?.sections.map((region) => (
                        { label: region.name, onClick: (newsItem) => handleMoveToSection(newsItem, region.name) }
                    )) || []

            }
        }, {
            icon: <SparklesIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Add to Highlights',
            options: {
                onClick: (newsItem) => handleAddToHighlights(newsItem),
            }
        }, {
            icon: <XCircleIcon className="h-5 w-5 text-red-500 hover:text-red-700" />,
            title: 'Remove from Digest',
            options: {
                onClick: (newsItem) => handleDeleteFromDigest(newsItem),
            }
        },
    ]

    return (
        <div className="bg-gray-100 dark:bg-gray-800 min-h-screen flex flex-col">

            <main className="flex-grow p-4">
                <div className='flex  w-full space-x-4'>
                    <div className="bg-white dark:bg-gray-700 rounded-lg shadow-md p-4 w-full">
                        <div className='flex items-center'>
                            {isNewDigest ? (
                                <span className='text-xl font-bold text-gray-600 dark:text-white'>Weekly Newsletter Studio</span>
                            ) : (
                                <div className=''>
                                    <div className='text  text-gray-600 dark:text-white'>Weekly Newsletter Studio</div>
                                    <div className='inline-flex items-center space-x-2 text-xl font-bold text-gray-600'>
                                        <CalendarIcon className='h-5 w-5 text-gray-400' />
                                        <span>{digest?.start_date.toLocaleDateString()}</span>
                                        <CalendarIcon className='h-5 w-5 text-gray-400' />
                                        <span>{digest?.end_date.toLocaleDateString()}</span>
                                    </div>
                                </div>

                            )
                            }
                        </div>
                        {isNewDigest && (
                            <div className='flex  justify-between'>

                                <div className='w-3/5'>
                                    <h2 className="text-xl font-medium text-gray-600 dark:text-white mb-4">
                                        Settings
                                    </h2>
                                    <div className="flex space-x-4 mb-4">
                                        <div className="flex-1">
                                            <input
                                                type="text"
                                                ref={startDateRef}
                                                placeholder="Start Date & Time"
                                                className="w-full border border-gray-300 p-2 rounded focus:outline-none focus:border-blue-500 dark:bg-gray-600 dark:text-white dark:border-gray-600"
                                            />
                                        </div>

                                        <button onClick={handleGenerate} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none">
                                            Generate
                                        </button>
                                    </div>
                                </div>
                            </div>

                        )}


                    </div>
                </div>
                {(newsIsLoading || newsletterIsLoading || !isNewDigest) && (

                    <div className="bg-gray-100 dark:bg-gray-800 flex flex-col">
                        {/* Header remains the same */}
                        <main className="flex-grow p-4 flex">
                            <div className="w-4/12 flex-grow">
                                {newsIsLoading ? <NewsListSkeleton numberOfItems={4} /> : <NewsList news={news} buttons={newsListButtonsConfig} title='News from daily Newsletter' />}

                            </div>


                            <div className="w-6/12 flex-grow">
                                {newsletterIsLoading ? <NewsletterRendererSkeleton /> :
                                    <DigestRenderer digestData={digest} setDigestData={setDigest} contentbuttons={rendererButtonsConfig} highlightButtons={hightlightButtons} />}
                            </div>
                        </main>
                    </div>
                )}
            </main >
        </div >
    );
};


export default WeeklyDigest;