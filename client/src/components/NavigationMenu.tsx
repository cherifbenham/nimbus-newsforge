import React, { useState, useContext, useEffect } from "react";
import * as NavigationMenu from "@radix-ui/react-navigation-menu";
import classNames from "classnames";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import { NewsletterContext, NewsletterContextType } from '../context/NewsletterContext';
import ApiHelper from '../backend/ApiHelper';
import { NewsletterHeader } from '../dto/InterfaceDefinition';
import { motion } from 'framer-motion';
import { useNavigate } from "react-router-dom";
import MenuLoadingSkeleton from "./skeletons/MenuLoadingSkeleton"




interface ListItemProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
    title: string;
    children: React.ReactNode;
    onClick?: () => void;
}

const ListItem = React.forwardRef<HTMLAnchorElement, ListItemProps>(
    ({ className, children, title, onClick, ...props }, ref) => (
        <div>
            <NavigationMenu.Link asChild ref={ref} onClick={onClick}>
                <a
                    className={classNames(
                        "block select-none rounded-md p-3 text-[15px] leading-none no-underline outline-none transition-colors hover:bg-mauve3 focus:shadow-[0_0_0_2px] focus:shadow-violet7",
                        className,
                    )}
                    {...props}
                >
                    <div className="mb-[5px] font-medium leading-[1.2] dark:text-slate-100">
                        {title}
                    </div>
                    <div className="leading-[1.4]">{children}</div>
                </a>
            </NavigationMenu.Link>
        </div>
    ),
);

interface MenuItemProps {
    label: string;
    icon?: React.ReactNode;
    hasArrow?: boolean | false;
}
const MenuItem: React.FC<MenuItemProps> = ({ label, hasArrow }) => {
    return (
        <NavigationMenu.Trigger className="px-4 py-4 rounded text font-medium text-gray-700 dark:text-slate-100 hover:text-gray-800 dark:hover:text-slate-200 hover:font-bold ">
            {label}
            {hasArrow && (
                <ChevronDownIcon className="h-4 w-4 inline-block ml-1 text-gray-600 dark:text-slate-400" />
            )}

        </NavigationMenu.Trigger>
    )
}

const NavigationHeader = () => {
    const { setNlId, setIsNewDailyNL, setIsNewDigest, setDigestId } = useContext(NewsletterContext) as NewsletterContextType;
    const [dailyNews, setDailyNews] = useState<NewsletterHeader[]>([]);
    const [weeklyNews, setWeeklyNews] = useState<NewsletterHeader[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const navigate = useNavigate();


    useEffect(() => {
        const fetchNews = async () => {
            setIsLoading(true)
            const daily = await ApiHelper.getNewsletterHistory();
            const weekly = await ApiHelper.getDigestHistory();
            setDailyNews(daily);
            setWeeklyNews(weekly);
            setIsLoading(false)
        };
        fetchNews();
    }, []);

    return (
        <nav className="flex space-x-4 z-50">
            <NavigationMenu.Root>
                <NavigationMenu.List className="flex space-x-4 bg-white dark:bg-slate-700 rounded-full shadow-sm h-16 px-2 "> {/* Changed background */}
                    {/* Daily Menu */}
                    <NavigationMenu.Item >
                        <MenuItem label="Daily" hasArrow={true} />
                        <NavigationMenu.Content className="absolute right-0 mt-2 bg-white dark:bg-black rounded-md shadow-md py-2 w-60">
                            <div className='mx-4 mt-4'>
                                <div className='flex mb-8'>
                                    <motion.button
                                        whileHover={{ transition: { duration: 0.3 }, scale: 1.05 }}
                                        onClick={() => { setIsNewDailyNL(true); setNlId(null); navigate('/daily') }} className="flex items-center  bg-blue-500 hover:bg-blue-700 text-white font-bold rounded-full w-8 h-8 justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                                        </svg>
                                    </motion.button>
                                    <span className='text-base ml-2 font-bold text-gray-700 dark:text-slate-100 uppercase'>Create New</span>
                                </div>
                                <h2 className="text-lg font-medium mb-2 text-slate-500 dark:text-slate-400">Recent</h2>
                                {isLoading ? (<MenuLoadingSkeleton />) : (
                                    <>
                                        {dailyNews.map((item, index) => (
                                            <ListItem key={index} href="#" title="" onClick={() => { setNlId(item.id); setIsNewDailyNL(false); navigate('/daily') }}>
                                                <motion.div

                                                    className="flex items-center justify-between p-2 rounded"
                                                    whileHover={{ borderRadius: '10px', transition: { duration: 0.3 }, scale: 1.05 }}
                                                >
                                                    <div className="flex items-center w-full">
                                                        <div className="w-4 h-4">
                                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-4 h-4 dark:fill-white">
                                                                <path strokeLinecap="round" d="M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
                                                            </svg>
                                                        </div>
                                                        <span className="truncate ml-2 w-42 text-left dark:text-white">{item.publishDate.toDateString()}</span>
                                                    </div>

                                                </motion.div>

                                            </ListItem>
                                        ))}

                                    </>
                                )}


                            </div>
                        </NavigationMenu.Content>
                    </NavigationMenu.Item>
                    <NavigationMenu.Item>
                        <MenuItem label="Weekly" hasArrow={true} />
                        <NavigationMenu.Content className="absolute right-0 mt-2 bg-white dark:bg-black rounded-md shadow-md py-2 w-60">
                            <div className='mx-4 mt-4'>

                                <div className='flex mb-8'>
                                    <motion.button
                                        whileHover={{ transition: { duration: 0.3 }, scale: 1.05 }}
                                        onClick={() => { setIsNewDigest(true); setDigestId(null); navigate('/weekly') }} className="flex items-center  bg-blue-500 hover:bg-blue-700 text-white font-bold rounded-full w-8 h-8 justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                                        </svg>
                                    </motion.button>
                                    <span className='text-base ml-2 font-bold text-gray-700 dark:text-slate-100 uppercase'>Create New</span>
                                </div>
                                <h2 className="text-lg font-medium mb-2 text-slate-500 dark:text-slate-400">Recent</h2>
                                {isLoading ? (<MenuLoadingSkeleton />) : (
                                    <>
                                        {weeklyNews.map((item, index) => (
                                            <ListItem key={index} href="#" title="" onClick={() => { setDigestId(item.id); setIsNewDigest(false); navigate('/weekly') }}>
                                                <motion.div

                                                    className="flex items-center justify-between p-2 rounded"
                                                    whileHover={{ borderRadius: '10px', transition: { duration: 0.3 }, scale: 1.05 }}
                                                >
                                                    <div className="flex items-center w-full">
                                                        <div className="w-4 h-4">
                                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-4 h-4 dark:fill-white">
                                                                <path strokeLinecap="round" d="M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.282 48.282 0 0 0 5.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
                                                            </svg>
                                                        </div>
                                                        <span className="truncate ml-2 w-36 text-left dark:text-white">{item.publishDate.toDateString()}</span>
                                                    </div>

                                                </motion.div>

                                            </ListItem>
                                        ))}
                                    </>
                                )}
                            </div>
                        </NavigationMenu.Content>
                    </NavigationMenu.Item>


                    {/* Settings Menu */}
                    <NavigationMenu.Item>
                        <MenuItem label="Setup" />
                    </NavigationMenu.Item>
                </NavigationMenu.List>
                <NavigationMenu.Indicator className="hidden" />
            </NavigationMenu.Root>
        </nav>
    );
};



export default NavigationHeader;