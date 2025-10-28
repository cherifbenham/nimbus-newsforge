"use client"

import React, { useState, useRef, useEffect, useCallback, useContext, Suspense } from 'react';
import { NewsletterContext, NewsletterContextType } from "../context/NewsletterContext";
import flatpickr from "flatpickr";
import { News, Newsletter, NewsletterRegionSection } from '../dto/InterfaceDefinition';
import NewsletterRenderer from '../components/NewsletterRenderer';
import ApiHelper from '../backend/ApiHelper';
import NewsletterRendererSkeleton from '../components/skeletons/NewsletterSkeleton';
import { ButtonConfig, NewsListErrorFallBack } from "../components/NewsList2"
import { ArrowTrendingUpIcon, EllipsisHorizontalCircleIcon, GlobeAltIcon, CalendarIcon } from '@heroicons/react/24/outline';
import { XCircleIcon } from 'lucide-react';
import DailyNewsList from '../components/DailyNewsList';
import { ErrorBoundary } from 'react-error-boundary'
import NewsListSkeleton from '../components/skeletons/NewsListSkeleton';

interface DailyNewsletterProps { }

const DailyNewsletter: React.FC<DailyNewsletterProps> = () => {
    const [startDate, setStartDate] = useState<string | null>(null);
    const [endDate, setEndDate] = useState<string | null>(null);
    const [newsletter, setNewsletter] = useState<Newsletter | null>(null);
    const { nlId, isNewDailyNL, setIsNewDailyNL } = useContext(NewsletterContext) as NewsletterContextType;
    const [newsletterIsLoading, setNewsletterIsLoading] = useState(false)
    const [emailSubject, setEmailSubject] = useState<string>("")

    const startDateRef = useRef<HTMLInputElement>(null);
    const endDateRef = useRef<HTMLInputElement>(null);


    useEffect(() => {
        if (isNewDailyNL) {
            setNewsletter(null);
        }
    }, [isNewDailyNL])

    useEffect(() => {
        const loadNewsletter = async () => {
            if (!nlId) return;
            const newsletterData = await ApiHelper.getNewsletter(nlId);
            if (newsletterData) {
                setNewsletter(newsletterData);
                setStartDate(newsletterData.start_date.toISOString())
                setEndDate(newsletterData.end_date.toISOString())
            }
        };
        setNewsletterIsLoading(true);
        loadNewsletter();
        setNewsletterIsLoading(false);

    }, [nlId]);

    useEffect(() => {
        console.log(startDate, endDate)
    }, [startDate, endDate])


    const isValidSection = (section: string): section is keyof Newsletter["sections"] => {
        return ["topNews", "podcasts", "regionalNews", "moreStories"].includes(section);
    };


    const handleAddToSection = (newsItem: News, section: string, region?: string) => {
        const updatedNewsletter = { ...newsletter };
        if (!updatedNewsletter.sections) {
            updatedNewsletter.sections = {
                topNews: [],
                podcasts: [],
                regionalNews: [],
                moreStories: [],
            };
        }
        if (isValidSection(section)) {
            if (section === "regionalNews") {
                const regionalNews = updatedNewsletter.sections.regionalNews || [];
                const existingRegionIndex = regionalNews.findIndex(item => item.region === region);
                if (existingRegionIndex !== -1) {
                    const updatedRegionalNews = [...regionalNews];
                    updatedRegionalNews[existingRegionIndex].news.push(newsItem);
                    updatedNewsletter.sections.regionalNews = updatedRegionalNews;
                } else {
                    updatedNewsletter.sections.regionalNews = [...regionalNews, { region: region!, news: [newsItem] }];
                }

            } else {
                // Handle other sections (topNews, podcasts, moreStories)
                const sectionNews = updatedNewsletter.sections[section] || [];
                if (!sectionNews.find(item => item.url === newsItem.url)) {
                    updatedNewsletter.sections[section] = [...sectionNews, newsItem];
                }

            }
            if (updatedNewsletter.start_date && updatedNewsletter.end_date) {
                setNewsletter(updatedNewsletter as Newsletter); // Type assertion only when dates are defined.
            } else {
                console.error("Start and end dates are missing in the newsletter object.");
            }
        } else {
            console.error("Invalid section:", section);
        }
    };

    const handleMoveToSection = (newsItem: News, targetSection: string, sourceSection?: string, targetRegion?: string) => {
        const updatedNewsletter = { ...newsletter };

        // Handle undefined sections
        if (!updatedNewsletter.sections) {
            updatedNewsletter.sections = {
                topNews: [],
                podcasts: [],
                regionalNews: [],
                moreStories: [],
            };
            return;
        }

        if (!sourceSection || !isValidSection(sourceSection) || !isValidSection(targetSection)) {
            console.error("Invalid source or target section:", sourceSection, targetSection);
            return;
        }

        let sourceSectionNews: News[] | NewsletterRegionSection[];
        let sourceIndex: number;

        if (sourceSection === 'regionalNews') {
            sourceSectionNews = updatedNewsletter.sections.regionalNews || [];
            const newsItemIndex = sourceSectionNews.findIndex((regionItem) => regionItem.news.some(news => news.url === newsItem.url));
            if (newsItemIndex === -1) {
                console.error('News item not found');
                return;
            }
            const updatedRegionalNews = [...sourceSectionNews];
            updatedRegionalNews[newsItemIndex].news = updatedRegionalNews[newsItemIndex].news.filter(item => item.url !== newsItem.url);
            updatedNewsletter.sections.regionalNews = updatedRegionalNews;
            sourceIndex = newsItemIndex;
        } else {
            sourceSectionNews = updatedNewsletter.sections[sourceSection] || [];
            sourceIndex = sourceSectionNews.findIndex(item => item.url === newsItem.url);
        }

        // Check if item exists in source section
        if (sourceIndex === -1) {
            console.error("News item not found in source section:", newsItem.url, sourceSection);
            return;
        }

        // Remove from source section
        const updatedSourceSectionNews = sourceSectionNews.filter((_, index) => index !== sourceIndex);
        if (sourceSection === 'regionalNews') {
            updatedNewsletter.sections.regionalNews = updatedSourceSectionNews as NewsletterRegionSection[];
        } else {
            updatedNewsletter.sections[sourceSection] = updatedSourceSectionNews as News[];
        }

        // Add to target section
        if (targetSection === 'regionalNews') {
            const region = targetRegion || 'EMEA'; // Default to EMEA if no region is specified
            const regionalNewsList = updatedNewsletter.sections.regionalNews || [];
            const existingRegionIndex = regionalNewsList.findIndex((item) => item.region === region);
            if (existingRegionIndex !== -1) {
                // Update existing region
                const updatedRegionalNews = [...regionalNewsList];
                updatedRegionalNews[existingRegionIndex].news = [...updatedRegionalNews[existingRegionIndex].news, newsItem];
                updatedNewsletter.sections.regionalNews = updatedRegionalNews;
            } else {
                // Create new region entry
                updatedNewsletter.sections.regionalNews = [...regionalNewsList, { region, news: [newsItem] }];
            }
        } else {
            // Handle other sections
            const targetSectionNews = updatedNewsletter.sections[targetSection] || [];
            updatedNewsletter.sections[targetSection] = [...targetSectionNews, newsItem];
        }

        if (updatedNewsletter.start_date && updatedNewsletter.end_date) {
            setNewsletter(updatedNewsletter as Newsletter);
        } else {
            console.error("Start and end dates are missing in the newsletter object.");
        }
    };

    const handleDeleteFromSection = (newsItem: News, sourceSection: string) => {
        const updatedNewsletter = { ...newsletter };
        if (!updatedNewsletter.sections) {
            updatedNewsletter.sections = {
                topNews: [],
                podcasts: [],
                regionalNews: [],
                moreStories: [],
            };
            return;
        }

        if (!sourceSection || !isValidSection(sourceSection)) {
            console.error("Invalid source or target section:", sourceSection);
            return;
        }

        let sourceSectionNews: News[] | NewsletterRegionSection[];
        let sourceIndex: number;

        if (sourceSection === 'regionalNews') {
            sourceSectionNews = updatedNewsletter.sections.regionalNews || [];
            const newsItemIndex = sourceSectionNews.findIndex((regionItem) => regionItem.news.some(news => news.url === newsItem.url));
            if (newsItemIndex === -1) {
                console.error('News item not found');
                return;
            }
            const updatedRegionalNews = [...sourceSectionNews];
            updatedRegionalNews[newsItemIndex].news = updatedRegionalNews[newsItemIndex].news.filter(item => item.url !== newsItem.url);
            updatedNewsletter.sections.regionalNews = updatedRegionalNews;
            sourceIndex = newsItemIndex;
        } else {
            sourceSectionNews = updatedNewsletter.sections[sourceSection] || [];
            sourceIndex = sourceSectionNews.findIndex(item => item.url === newsItem.url);
        }

        // Remove from source section
        const updatedSourceSectionNews = sourceSectionNews.filter((_, index) => index !== sourceIndex);
        if (sourceSection === 'regionalNews') {
            updatedNewsletter.sections.regionalNews = updatedSourceSectionNews as NewsletterRegionSection[];
        } else {
            updatedNewsletter.sections[sourceSection] = updatedSourceSectionNews as News[];
        }


        if (updatedNewsletter.start_date && updatedNewsletter.end_date) {
            setNewsletter(updatedNewsletter as Newsletter);
        } else {
            console.error("Start and end dates are missing in the newsletter object.");
        }


    }

    const buttonsConfig: ButtonConfig[] = [
        {
            icon: <ArrowTrendingUpIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Add to Top Stories',
            options: {
                onClick: (newsItem) => handleAddToSection(newsItem, 'topNews'),
            }
        },
        {
            icon: <GlobeAltIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Add to Regional News',
            options: {
                dropdownItems:
                    ["North America", "Latin America", "Europe", "Asia Pacific", "Middle East & Africa"].map((region) => (
                        { label: region, onClick: (newsItem) => handleAddToSection(newsItem, 'regionalNews', region) }
                    ))

            }
        }, {
            icon: <EllipsisHorizontalCircleIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Add to More Stories',
            options: {
                onClick: (newsItem) => handleAddToSection(newsItem, 'moreStories'),
            }
        },
    ]

    const rendererButtonsConfig: ButtonConfig[] = [
        {
            icon: <ArrowTrendingUpIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Move to Top Stories',
            options: {
                onClick: (newsItem, sourceSection) => handleMoveToSection(newsItem, 'topNews', sourceSection)
            }
        },
        {
            icon: <GlobeAltIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Move to Regional News',
            options: {
                dropdownItems:
                    ["North America", "Latin America", "Europe", "Asia Pacific", "Middle East & Africa"].map((region) => (
                        { label: region, onClick: (newsItem, sourceSection) => handleMoveToSection(newsItem, 'regionalNews', sourceSection, region) }
                    ))

            }
        }, {
            icon: <EllipsisHorizontalCircleIcon className="h-5 w-5 text-blue-500 hover:text-blue-700" />,
            title: 'Move to More Stories',
            options: {
                onClick: (newsItem, sourceSection) => handleMoveToSection(newsItem, 'moreStories', sourceSection),
            }
        }, {
            icon: <XCircleIcon className="h-5 w-5 text-red-500 hover:text-red-700" />,
            title: 'Move to More Stories',
            options: {
                onClick: (newsItem, sourceSection) => handleDeleteFromSection(newsItem, sourceSection),
            }
        }
    ]

    const handleGenerate = async () => {
        if (startDate && endDate) {
            const startDateObj = new Date(startDate.toString());
            const endDateObj = new Date(endDate.toString());
            // loadNewsForPeriod(startDateObj, endDateObj)
            setNewsletterIsLoading(true);
            const newsletterData = await ApiHelper.generateNewsletter(startDateObj, endDateObj);
            setNewsletter(newsletterData);
            setIsNewDailyNL(false)
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
                    setState(date.toISOString());
                },
            });
            return () => fp.destroy();
        }
        return () => { };
    }, []);

    useEffect(() => {
        if (isNewDailyNL) {
            // Initialize Flatpickr only when the input elements are rendered
            const cleanupStartDate = initializeFlatpickr(startDateRef, setStartDate);
            const cleanupEndDate = initializeFlatpickr(endDateRef, setEndDate);
            return () => {
                cleanupStartDate();
                cleanupEndDate();
            };
        }
    }, [isNewDailyNL, initializeFlatpickr, setStartDate, setEndDate]);


    return (
        <div className="bg-gray-100 dark:bg-gray-800 flex-grow">

            <main className="flex-grow p-4">
                <div className='flex  w-full space-x-4'>
                    <div className="bg-white dark:bg-gray-700 rounded-lg shadow-md p-6 w-full">
                        <div className='flex items-center'>
                            {isNewDailyNL ? (
                                <span className='text-xl font-bold text-gray-600 dark:text-white'>Daily Newsletter Studio</span>
                            ) : (
                                <div className=''>
                                    <div className='text  text-gray-600 dark:text-white'>Daily Newsletter Studio</div>
                                    <div className='inline-flex items-center space-x-2 text-xl font-bold text-gray-600'>
                                        <CalendarIcon className='h-5 w-5 text-gray-400' />
                                        <span>{newsletter?.start_date.toLocaleDateString()}</span>
                                        <CalendarIcon className='h-5 w-5 text-gray-400' />
                                        <span>{newsletter?.end_date.toLocaleDateString()}</span>
                                    </div>
                                </div>

                            )
                            }
                        </div>
                        {isNewDailyNL && (
                            <div className='flex  justify-between'>

                                <div className='w-3/5'>
                                    <h2 className="text-xl font-medium text-gray-600 dark:text-white mb-4">
                                        Settings
                                    </h2>
                                    <div className="flex space-x-4 mb-4 items-center">
                                        <div className="flex-1">
                                            <input
                                                type="text"
                                                ref={startDateRef}
                                                placeholder="Start Date & Time"
                                                className="w-full border border-gray-300 p-2 rounded focus:outline-none focus:border-blue-500 dark:bg-gray-600 dark:text-white dark:border-gray-600"
                                            />
                                        </div>
                                        <div className="flex-1">
                                            <input
                                                type="text"
                                                ref={endDateRef}
                                                placeholder="End Date & Time"
                                                className="w-full border border-gray-300 p-2 rounded focus:outline-none focus:border-blue-500 dark:bg-gray-600 dark:text-white dark:border-gray-600"
                                            />
                                        </div>
                                        <div className="flex-1">
                                            <input
                                                type="text"
                                                value={emailSubject}
                                                onChange={(e) => setEmailSubject(e.target.value)}
                                                placeholder="Email subject (optional)"
                                                className="w-full border border-gray-300 p-2 rounded focus:outline-none focus:border-blue-500 dark:bg-gray-600 dark:text-white dark:border-gray-600"
                                            />
                                        </div>
                                        <button onClick={handleGenerate} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none">
                                            Generate
                                        </button>
                                        {newsletter && (
                                            <button
                                                onClick={async () => {
                                                    try {
                                                        const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                                        const subjectHint = emailSubject || defaultHint;
                                                        const { subject, html } = await ApiHelper.composeEmailFromNewsletter(newsletter!, subjectHint);
                                                        const win = window.open('', '_blank');
                                                        if (win) {
                                                            win.document.title = subject || 'Newsletter Email';
                                                            win.document.write(html);
                                                            win.document.close();
                                                        }
                                                    } catch (e) {
                                                        console.error('Error composing email', e);
                                                    }
                                                }}
                                                className="ml-2 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                            >
                                                Compose Email
                                            </button>
                                        )}
                                        {newsletter && (
                                            <button
                                                onClick={async () => {
                                                    try {
                                                        const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                                        const subjectHint = emailSubject || defaultHint;
                                                        const { subject, html } = await ApiHelper.composeEmailFromNewsletter(newsletter!, subjectHint);
                                                        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
                                                        const url = URL.createObjectURL(blob);
                                                        const a = document.createElement('a');
                                                        a.href = url;
                                                        const safeName = (subject || 'newsletter_email').replace(/[^a-z0-9\-_]+/gi,'_').slice(0,60);
                                                        a.download = `${safeName}.html`;
                                                        document.body.appendChild(a);
                                                        a.click();
                                                        a.remove();
                                                        // Delay revocation to avoid cancelling the download in some browsers
                                                        setTimeout(() => URL.revokeObjectURL(url), 2000);
                                                    } catch (e) {
                                                        console.error('Error downloading email HTML', e);
                                                    }
                                                }}
                                                className="ml-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                            >
                                                Download HTML
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>

                        )}

                        {newsletter && (
                            <div className="flex space-x-2 mt-3">
                                <input
                                    type="text"
                                    value={emailSubject}
                                    onChange={(e) => setEmailSubject(e.target.value)}
                                    placeholder="Email subject (optional)"
                                    className="flex-1 border border-gray-300 p-2 rounded focus:outline-none focus:border-blue-500 dark:bg-gray-600 dark:text-white dark:border-gray-600"
                                />
                                <button
                                    onClick={async () => {
                                        try {
                                            const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                            const subjectHint = emailSubject || defaultHint;
                                            const { subject, html } = await ApiHelper.composeEmailFromNewsletter(newsletter!, subjectHint);
                                            const win = window.open('', '_blank');
                                            if (win) {
                                                win.document.title = subject || 'Newsletter Email';
                                                win.document.write(html);
                                                win.document.close();
                                            }
                                        } catch (e) {
                                            console.error('Error composing email', e);
                                        }
                                    }}
                                    className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                >
                                    Compose Email
                                </button>
                                <button
                                    onClick={async () => {
                                        try {
                                            const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                            const subjectHint = emailSubject || defaultHint;
                                            const { subject, html } = await ApiHelper.composeCuratedEmailFromNewsletter(newsletter!, subjectHint, 5);
                                            const win = window.open('', '_blank');
                                            if (win) {
                                                win.document.title = subject || 'Newsletter Email';
                                                win.document.write(html);
                                                win.document.close();
                                            }
                                        } catch (e) {
                                            console.error('Error composing curated email', e);
                                        }
                                    }}
                                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                >
                                    Curate & Compose
                                </button>
                                <button
                                    onClick={async () => {
                                        try {
                                            const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                            const subjectHint = emailSubject || defaultHint;
                                            const { subject, html } = await ApiHelper.composeEmailFromNewsletter(newsletter!, subjectHint);
                                            const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = `${(subject || 'newsletter').replace(/[^a-z0-9\-_]+/gi,'_').slice(0,60)}.html`;
                                            document.body.appendChild(a);
                                            a.click();
                                            a.remove();
                                            setTimeout(() => URL.revokeObjectURL(url), 2000);
                                        } catch (e) {
                                            console.error('Error downloading email HTML', e);
                                        }
                                    }}
                                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                >
                                    Download HTML
                                </button>
                                <button
                                    onClick={async () => {
                                        try {
                                            const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                            const subjectHint = emailSubject || defaultHint;
                                            const { subject, html } = await ApiHelper.composeCuratedEmailFromNewsletter(newsletter!, subjectHint, 5);
                                            const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            const safeName = ((subject || 'newsletter_curated') + '').replace(/[^a-z0-9\-_]+/gi,'_').slice(0,60);
                                            a.download = `${safeName}.html`;
                                            document.body.appendChild(a);
                                            a.click();
                                            a.remove();
                                            setTimeout(() => URL.revokeObjectURL(url), 2000);
                                        } catch (e) {
                                            console.error('Error downloading curated email HTML', e);
                                        }
                                    }}
                                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                >
                                    Curate & Download
                                </button>
                                <button
                                    onClick={async () => {
                                        try {
                                            const defaultHint = `${new Date(startDate!).toLocaleDateString()} - ${new Date(endDate!).toLocaleDateString()}`;
                                            const subjectHint = emailSubject || defaultHint;
                                            const { html } = await ApiHelper.composeEmailFromNewsletter(newsletter!, subjectHint);
                                            if (navigator.clipboard && navigator.clipboard.writeText) {
                                                await navigator.clipboard.writeText(html);
                                                window.alert('Email HTML copied to clipboard');
                                            } else {
                                                const ta = document.createElement('textarea');
                                                ta.value = html;
                                                document.body.appendChild(ta);
                                                ta.select();
                                                document.execCommand('copy');
                                                ta.remove();
                                                window.alert('Email HTML copied to clipboard');
                                            }
                                        } catch (e) {
                                            console.error('Error copying email HTML', e);
                                        }
                                    }}
                                    className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded focus:outline-none"
                                >
                                    Copy HTML
                                </button>
                            </div>
                        )}

                    </div>
                </div>
                {(newsletterIsLoading || !isNewDailyNL) && (

                    <div className="bg-gray-100 dark:bg-gray-800 flex flex-col">
                        {/* Header remains the same */}
                        <main className="flex-grow p-4 flex">
                            <div className="w-4/12 flex-grow">
                                {startDate && endDate && (
                                    <ErrorBoundary FallbackComponent={NewsListErrorFallBack}>
                                        <Suspense fallback={<NewsListSkeleton numberOfItems={3} />}>
                                            <DailyNewsList newsletter={newsletter} title="Top Stories" buttons={buttonsConfig} start_date={startDate} end_date={endDate} />
                                        </Suspense>
                                    </ErrorBoundary>
                                )}

                            </div>


                            <div className="w-6/12 flex-grow">
                                {newsletterIsLoading ? <NewsletterRendererSkeleton /> :
                                    <NewsletterRenderer newsletterData={newsletter} buttons={rendererButtonsConfig} />}
                            </div>
                        </main>
                    </div>
                )}
            </main >
        </div >
    );
};




export default DailyNewsletter;
