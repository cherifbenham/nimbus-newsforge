import React, { useEffect, useState } from 'react';
import { News } from '../dto/InterfaceDefinition';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as ToggleGroup from "@radix-ui/react-toggle-group";
import * as HoverCard from "@radix-ui/react-hover-card";
import ApiHelper from '../backend/ApiHelper';
import { marked } from 'marked';
import axios from 'axios';




export interface ButtonConfig {
    icon: React.ReactNode;
    title: string;
    className?: string;
    options: {
        onClick?: (item: News, ...args: any[]) => void;
        dropdownItems?: { label: string; onClick: (item: News, ...args: any[]) => void }[];
    } & (
        { onClick?: never; dropdownItems: { label: string; onClick: (item: News, ...args: any[]) => void }[] } |
        { onClick: (item: News, ...args: any[]) => void; dropdownItems?: never }
    );

}

export interface SortingConfig {
    current_value: string,
    callback: (option: string) => void;
    options: SortingOption[];
}

export interface SortingOption {
    icon: React.ReactNode;
    title: string;
    option_key: string;
}

interface NewsItemProps {
    news: News;
    section?: string;
    buttons: ButtonConfig[]; // Array of button configurations
}

export const GeminiNewsHover: React.FC<{ newsItem: News }> = ({ newsItem }) => {
    const [loading, setLoading] = useState(false)
    const [analysis, setAnalysis] = useState("")
    const [open, setOpen] = useState(false);


    const getAnalysis = async () => {
        setLoading(true)
        const data = await ApiHelper.analyzeNews(newsItem)
        setAnalysis(data)
        setLoading(false)
    }

    React.useEffect(() => {
        if (!open) return;
        getAnalysis()
    }, [open])





    return (
        <HoverCard.Root open={open} onOpenChange={setOpen}>
            <HoverCard.Trigger asChild>
                <a href={newsItem.url} target="_blank" rel="noopener noreferrer"><h3 className="text-lg font-medium text-gray-800">{newsItem.title}  </h3></a>
            </HoverCard.Trigger>
            <HoverCard.Portal>
                <HoverCard.Content
                    className="w-[400px] rounded-md bg-white p-5 shadow-[hsl(206_22%_7%_/_35%)_0px_10px_38px_-10px,hsl(206_22%_7%_/_20%)_0px_10px_20px_-15px] data-[side=bottom]:animate-slideUpAndFade data-[side=left]:animate-slideRightAndFade data-[side=right]:animate-slideLeftAndFade data-[side=top]:animate-slideDownAndFade data-[state=open]:transition-all"
                    sideOffset={5}
                >
                    <div className="flex flex-col space-y-4">
                        <div className="inline-flex items-center space-x-2">
                            <img src='spark.png' className='h-5 w-5' />
                            <span className='text-lg font-bold text-gray-600'>Gemini Analysis</span>
                        </div>
                        <div className="flex flex-col px-5 text-slate-700">
                            {loading ? (
                                <span className="" >Loading...</span>
                            ) : (
                                <div className="flex flex-col px-5 text-slate-700" dangerouslySetInnerHTML={{ __html: marked(analysis) }} />
                            )}
                        </div>
                    </div>
                    <HoverCard.Arrow className="fill-white" />
                </HoverCard.Content>
            </HoverCard.Portal>
        </HoverCard.Root >
    )

}

export const NewsItem: React.FC<NewsItemProps> = ({ news, buttons, section }) => {
    const [open, setOpen] = useState(false);
    return (
        <div className={`${news.is_in_newsletter ? "bg-slate-200" : "bg-white"} flex-col shadow-md rounded-lg overflow-hidden mb-4`}>

            <div className="flex items-center p-4">
                <div>
                    {
                        news.is_in_newsletter && (
                            <span className='bg-gray-100 text-gray-700  text-xs mb-4 font-medium mr-2 px-2 py-1 rounded-full'>Published</span>
                        )
                    }
                    <div className="flex items-start  space-x-2">
                        <GeminiNewsHover newsItem={news} />

                    </div>
                    <p className="text-sm text-gray-600">{news.abstract}</p>
                </div>
            </div>
            <div className="flex border-t border-gray-200 p-4">
                <div className='inline-flex'>
                    <p className="text-xs text-gray-500">{news.website}</p>
                    <p className="text-xs text-gray-500">{news.publishDate?.toLocaleDateString()}</p>
                </div>
                {
                    !news.is_in_newsletter && (
                        <div className="flex space-x-2 ml-auto">
                            {buttons.map((button, index) => (
                                <React.Fragment key={index}> {/* Use Fragment to avoid extra divs */}
                                    {button.options.dropdownItems ? (
                                        <DropdownMenu.Root>
                                            <DropdownMenu.Trigger asChild>
                                                <button
                                                    title={button.title}
                                                    onClick={() => setOpen(!open)}
                                                    className={`${button.className} cursor-pointer`}
                                                >
                                                    {button.icon}
                                                </button>
                                            </DropdownMenu.Trigger>
                                            <DropdownMenu.Portal>
                                                <DropdownMenu.Content className="bg-white rounded-md shadow-md absolute mt-2 w-48">
                                                    {button.options.dropdownItems.map((item) => (
                                                        <DropdownMenu.Item
                                                            key={item.label}
                                                            className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                                                            onClick={() => item.onClick(news, section, item)}
                                                        >
                                                            {item.label}
                                                        </DropdownMenu.Item>
                                                    ))}
                                                </DropdownMenu.Content>
                                            </DropdownMenu.Portal>
                                        </DropdownMenu.Root>
                                    ) : (
                                        <button
                                            title={button.title}
                                            onClick={() => button.options.onClick?.(news, section) ?? (() => { })}
                                            className={`${button.className} cursor-pointer`}
                                        >
                                            {button.icon}
                                        </button>
                                    )}
                                </React.Fragment>
                            ))}
                        </div>
                    )}
            </div>
        </div>
    );
};

const NewsList: React.FC<{ title: string, news: News[]; buttons: ButtonConfig[]; sortConfig?: SortingConfig }> = ({ title, news, buttons, sortConfig }) => { //Buttons are passed as prop now.
    return (
        <div className="flex flex-col overflow-y-auto p-4 rounded-lg">
            <NewsListTitle title={title} sortConfig={sortConfig} />
            <div className="max-h-[700px] overflow-y-auto">
                {news.map((item, index) => (
                    <NewsItem key={index} news={item} buttons={buttons} />
                ))}
            </div>
        </div>
    );
};

export const NewsListTitle: React.FC<{ title: string, sortConfig?: SortingConfig }> = ({ title, sortConfig }) => {
    return (
        <div className="bg-white shadow-md rounded-lg mb-4 ">
            <div className="items-center p-4 flex">
                <div className="items-center flex space-x-2">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.242 5.992h12m-12 6.003H20.24m-12 5.999h12M4.117 7.495v-3.75H2.99m1.125 3.75H2.99m1.125 0H5.24m-1.92 2.577a1.125 1.125 0 1 1 1.591 1.59l-1.83 1.83h2.16M2.99 15.745h1.125a1.125 1.125 0 0 1 0 2.25H3.74m0-.002h.375a1.125 1.125 0 0 1 0 2.25H2.99" />
                    </svg>

                    <h2 className="text-lg font-bold text-gray-600">{title}</h2>
                </div>
                {sortConfig && sortConfig.options && sortConfig.options.length > 0 && (
                    <ToggleGroup.Root
                        className="inline-flex space-x-px rounded ml-auto "
                        type="single"
                        value={sortConfig.current_value}
                        onValueChange={(value) => {
                            if (value) sortConfig.callback(value);
                        }}
                        aria-label="Text alignment"
                    >
                        {sortConfig.options.map((option) => (
                            <ToggleGroup.Item
                                className="flex size-[35px] outline outline-1 outline-blue-200 items-center justify-center bg-white text-blue-400 leading-4 first:rounded-l last:rounded-r hover:bg-blue-100 hover:text-white focus:z-10   data-[state=on]:bg-blue-400 data-[state=on]:text-white"
                                value={option.option_key}
                                key={option.option_key}

                            >
                                {option.icon}
                            </ToggleGroup.Item>
                        )
                        )}
                    </ToggleGroup.Root>

                )}
            </div>
        </div>

    )
}

export const NewsListErrorFallBack = ({ error, resetErrorBoundary }: { error: Error, resetErrorBoundary: () => void }) => {
    const [errorMsg, setErrorMsg] = useState(error.message);

    useEffect(() => {
        // if this is an error coming from Axios, display the message from the server
        if (axios.isAxiosError(error)) {
            console.log(error)
            if (error.response?.data) {
                setErrorMsg(error.response.data)
            }
        }
    }, [error])




    return (

        <div className="text-center p-4">
            <NewsListTitle title="Something went wrong" />
            <div className="bg-red-300 flex-col shadow-md rounded-lg overflow-hidden mb-4">

                <div className="flex items-center p-4">
                    Error: {errorMsg}
                </div>
                <button
                    onClick={resetErrorBoundary}
                    className="my-4 bg-slate-500 text-white p-2 rounded"
                >
                    Try Again
                </button>
            </div>

        </div>

    );

}

export default NewsList;