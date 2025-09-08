import React, { useState } from 'react';
import { News } from '../dto/InterfaceDefinition';
import { ArrowTrendingUpIcon, GlobeAltIcon, EllipsisHorizontalCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

interface NewsItemProps {
    news: News;
    section?: string;
    handleAction?: (item: News, targetSection: string, sourceSection?: string, targetRegion?: string) => void;
}

export const NewsItem: React.FC<NewsItemProps> = ({ news, handleAction, section }) => {
    const [open, setOpen] = useState(false);

    return (
        <div className="bg-white shadow-md rounded-lg overflow-hidden mb-4">
            <div className="flex items-center p-4">

                <div>
                    <h3 className="text-lg font-medium text-gray-800">{news.title}</h3>
                    <p className="text-sm text-gray-600">{news.abstract}</p>
                </div>
            </div>
            <div className="flex border-t border-gray-200 p-4">
                <div className='inline-flex'>
                    <p className="text-xs text-gray-500">{news.website}</p>
                    <p className="text-xs text-gray-500">{news.publishDate?.toLocaleDateString()}</p> {/*Optional date*/}
                </div>
                <div className="flex space-x-2  ml-auto">
                    <button title="Add to Top Stories" onClick={() => handleAction?.(news, 'topNews', section)}><ArrowTrendingUpIcon className="h-5 w-5 text-blue-500 hover:text-blue-700 cursor-pointer" /></button>
                    <DropdownMenu.Root>
                        <DropdownMenu.Trigger asChild>
                            <button title="Add to Regional News" onClick={() => setOpen(!open)}>
                                <GlobeAltIcon className="h-5 w-5 text-blue-500 hover:text-blue-700 cursor-pointer" />
                            </button>
                        </DropdownMenu.Trigger>
                        <DropdownMenu.Portal>
                            <DropdownMenu.Content className="bg-white rounded-md shadow-md absolute mt-2 w-48">
                                {["North America", "Latin America", "Europe", "Asia Pacific", "Middle East & Africa"].map((region, index) => (
                                    <DropdownMenu.Item key={index} className="px-4 py-2 hover:bg-gray-100 cursor-pointer" onClick={() => handleAction?.(news, 'regionalNews', section, region)}>
                                        {region}
                                    </DropdownMenu.Item>
                                ))}
                            </DropdownMenu.Content>
                        </DropdownMenu.Portal>
                    </DropdownMenu.Root>

                    <button title="Add to More Stories" onClick={() => handleAction?.(news, 'moreStories', section)}><EllipsisHorizontalCircleIcon className="h-5 w-5 text-blue-500 hover:text-blue-700 cursor-pointer" /></button>
                    <button title="Remove" onClick={() => console.log("Removing")}><XCircleIcon className="h-5 w-5 ml-2 text-red-500 hover:text-red-700 cursor-pointer" /></button>
                </div>
            </div>

        </div>
    );
};

export const NewsListTitle = () => {
    return (
        <div className="bg-white shadow-md rounded-lg mb-4 ">
            <div className="items-center p-4 flex space-x-2">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.242 5.992h12m-12 6.003H20.24m-12 5.999h12M4.117 7.495v-3.75H2.99m1.125 3.75H2.99m1.125 0H5.24m-1.92 2.577a1.125 1.125 0 1 1 1.591 1.59l-1.83 1.83h2.16M2.99 15.745h1.125a1.125 1.125 0 0 1 0 2.25H3.74m0-.002h.375a1.125 1.125 0 0 1 0 2.25H2.99" />
                </svg>

                <h2 className="text-lg font-bold text-gray-600">Ranked News</h2>
            </div>
        </div>

    )
}

const NewsList: React.FC<{ news: News[], handleAction?: (item: News, section: string, region?: string) => void }> = ({ news, handleAction }) => {
    return (
        <div className="flex flex-col  overflow-y-auto p-4 rounded-lg">
            <NewsListTitle />
            <div className="max-h-[700px] overflow-y-auto">

                {news.map((item, index) => (
                    <NewsItem key={index} news={item} handleAction={handleAction} />
                ))}
            </div>
        </div>
    );
};

export default NewsList;