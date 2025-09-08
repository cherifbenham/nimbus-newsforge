import React, { useContext } from 'react';
import { Newsletter } from '../dto/InterfaceDefinition'; // Adjust path if needed
import { NewsItem } from './NewsList2';
import { Save } from 'lucide-react';
import ApiHelper from '../backend/ApiHelper';
import { NewsletterContext, NewsletterContextType } from '../context/NewsletterContext';
import { ButtonConfig } from './NewsList2';

interface NewsletterRendererProps {
    newsletterData: Newsletter | null;
    buttons: ButtonConfig[];
}


interface NewsletterSectionHeader {
    title: string;
    icon: React.ReactNode;
}
const NewsletterSectionHeader: React.FC<NewsletterSectionHeader> = ({ title, icon }) => {
    return (
        <div className="bg-slate-200 shadow-md rounded-lg mb-4 ml-6">
            <div className="items-center p-4 flex space-x-3">
                {icon}
                <h2 className="text-md font-bold text-gray-800">{title}</h2>
            </div>
        </div>
    )
}


const WorldIcon = () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
</svg>

const TrendIcon = () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
</svg>

const MoreIcon = () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
</svg>

const MicrophoneIcon = () => <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
</svg>




const NewsletterRenderer: React.FC<NewsletterRendererProps> = ({ newsletterData, buttons }) => {
    const { nlId, setNlId, setIsNewDailyNL } = useContext(NewsletterContext) as NewsletterContextType


    const handleSave = async () => {
        // Call the Save API
        if (!newsletterData) return;
        if (!nlId) {
            console.log(newsletterData)
            const newsletterId = await ApiHelper.saveNewsletter(newsletterData);
            setNlId(newsletterId);
            setIsNewDailyNL(false);

        } else {
            await ApiHelper.saveNewsletter(newsletterData, nlId);
        }
    }

    const handleDelete = async () => {
        if (nlId) {
            await ApiHelper.deleteNewsletter(nlId);
            setNlId(null);
            setIsNewDailyNL(true);
        }
    }


    return (
        <div className="p-4  rounded-lg">
            <div className="bg-white shadow-md rounded-lg mb-4 flex">
                <div className="items-center p-4 flex space-x-3">
                    <img src='/spark.png' alt='logo' className='w-8 h-8' />
                    <h3 className="text-lg font-bold text-gray-600">Generated Newsletter</h3>
                </div>
                <div className='flex  justify-between ml-auto space-x-4 mr-8 items-center'>

                    <button onClick={handleSave} className=" inline-flex items-center w-24 h-8 px-4  text-sm bg-blue-500 transition-colors duration-150 rounded-lg focus:shadow-outline hover:bg-blue-700 text-white font-bold 
                     focus:outline-none">
                        <Save className='mr-2' size={20} />
                        Save
                    </button>
                    <button onClick={handleDelete} className="bg-red-400  hover:bg-red-500 h-8 px-4 transition-colors duration-150 rounded-lg focus:shadow-outline text-sm text-white font-bold focus:outline-none">
                        Delete
                    </button>
                </div>
            </div >
            {
                newsletterData && (
                    <div className='overflow-y-auto max-h-[700px]'>
                        {newsletterData.sections.topNews && newsletterData.sections.topNews?.length > 0 && (
                            <div>
                                <NewsletterSectionHeader title="Top News" icon={<TrendIcon />} />
                                <ul className='ml-16'>
                                    {newsletterData.sections.topNews.map((news, index) => (
                                        <NewsItem key={index} news={news} section="topNews" buttons={buttons} />
                                    ))}
                                </ul>
                            </div>
                        )}

                        {newsletterData.sections.podcasts && newsletterData.sections.podcasts?.length > 0 && (
                            <div>
                                <NewsletterSectionHeader title="Podcast" icon={<MicrophoneIcon />} />
                                <ul className='ml-16'>
                                    {newsletterData.sections.podcasts.map((news, index) => (
                                        <NewsItem key={index} news={news} section="podcast" buttons={buttons} />
                                    ))}
                                </ul>
                            </div>
                        )}

                        {newsletterData.sections.regionalNews && newsletterData.sections.regionalNews.length > 0 && (
                            <div>
                                <NewsletterSectionHeader title="Regional News" icon={<WorldIcon />} />
                                {newsletterData.sections.regionalNews.map(regionalList => (
                                    <div key={regionalList.region} className="mb-4 ml-16">
                                        <div className="bg-slate-100 shadow-md rounded-lg mb-4 ">
                                            <div className="items-center p-4">
                                                <h2 className="text-lg font-bold  text-gray-800">{regionalList.region}</h2>
                                            </div>
                                        </div>
                                        <ul className=''>
                                            {regionalList.news.map((news, index) => (
                                                <NewsItem key={index} news={news} section="regionalNews" buttons={buttons} />
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        )}

                        {newsletterData.sections.moreStories && newsletterData.sections.moreStories?.length > 0 && (
                            <div>
                                <NewsletterSectionHeader title="More Stories" icon={<MoreIcon />} />
                                <ul className='ml-16'>
                                    {newsletterData.sections.moreStories.map((news, index) => (
                                        <NewsItem key={index} news={news} section="moreStories" buttons={buttons} />
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )
            }

        </div >
    );
};

export default NewsletterRenderer;