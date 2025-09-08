import React, { useEffect, useState, useContext } from 'react';
import ApiHelper from '../backend/ApiHelper';
import { motion } from 'framer-motion';
import { NewsletterHeader } from '../dto/InterfaceDefinition';
import { NewsletterContext, NewsletterContextType } from '../context/NewsletterContext';

interface SidebarProps {

}

const Sidebar: React.FC<SidebarProps> = () => {
    const [nlList, setNlList] = useState<NewsletterHeader[]>([]);
    const [displayedNLList, setDisplayedNLList] = useState<NewsletterHeader[]>([]);
    const [showMore, setShowMore] = useState(false);
    const { setNlId, setIsNewDailyNL } = useContext(NewsletterContext) as NewsletterContextType;

    useEffect(() => {
        const fetchNLHistory = async () => {
            const nlHistory = await ApiHelper.getNewsletterHistory();
            setNlList(nlHistory);
            setDisplayedNLList(nlHistory.slice(0, 5));
        };
        fetchNLHistory();
    }, []);

    const startNewDailyNL = () => {
        setNlId(null);
        setIsNewDailyNL(true);
    };




    const handleShowMore = () => {
        setShowMore(true);
        setDisplayedNLList(nlList.slice(0, displayedNLList.length + 5));
    };

    return (
        <aside className="w-64 bg-customer-blue dark:bg-black shadow-md md:block flex flex-col h-screen sticky top-0">
            <div className='my-8 mx-auto flex justify-center'>
                <img src='/amadeus-logo-dark-sky.png' alt='logo' />

            </div>
            <div className="p-4 flex-grow mt-32">
                <div className='flex items-center mb-8 '>
                    <motion.button
                        whileHover={{ transition: { duration: 0.3 }, scale: 1.05 }}
                        onClick={startNewDailyNL} className="flex items-center  bg-blue-500 hover:bg-blue-700 text-white font-bold rounded-full w-12 h-12 justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                    </motion.button>
                    <span className='text-base ml-2 font-bold text-gray-700 dark:text-slate-100 uppercase'>Create New</span>
                </div>
                <div className="mb-4">
                    <h2 className="text-lg font-medium mb-2 dark:text-slate-400">Recent</h2>
                    <ul className="space-y-2 ml-2">
                        {displayedNLList.map(({ publishDate, id }) => (
                            <motion.li
                                key={id}
                                className="flex items-center justify-between p-2 rounded"
                                whileHover={{ borderRadius: '10px', transition: { duration: 0.3 }, scale: 1.05 }}
                            >
                                <button onClick={() => setNlId(id)} className="flex items-center w-full">
                                    <div className="w-4 h-4">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-4 h-4 dark:fill-white">
                                            <path strokeLinecap="round" d="M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
                                        </svg>
                                    </div>
                                    <span className="truncate ml-2 w-36 text-left dark:text-white">{publishDate.toDateString()}</span>
                                </button>
                                <button className="text-gray-500">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-6 h-6">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5ZM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5ZM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5Z" />
                                    </svg>
                                </button>
                            </motion.li>
                        ))}
                        {nlList.length > 5 && !showMore && <li className="text-center text-sm text-gray-500 dark:text-slate-400"><button onClick={handleShowMore}>Show More</button></li>}
                    </ul>
                </div>
                <div className="p-4  fixed bottom-12">
                    <motion.button onClick={() => console.log("clicked")} whileHover={{ borderRadius: '10px', transition: { duration: 0.3 }, scale: 1.05 }} className="flex items-center  text-gray-700 dark:text-slate-400 font-bold py-2 px-4 rounded w-full">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 0 1 1.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.559.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.894.149c-.424.07-.764.383-.929.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 0 1-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.398.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 0 1-.12-1.45l.527-.737c.25-.35.272-.806.108-1.204-.165-.397-.506-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.108-1.204l-.526-.738a1.125 1.125 0 0 1 .12-1.45l.773-.773a1.125 1.125 0 0 1 1.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894Z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                        </svg>

                        Settings
                    </motion.button>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;