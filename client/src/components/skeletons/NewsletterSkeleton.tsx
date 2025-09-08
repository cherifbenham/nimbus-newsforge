import React from 'react';


interface NewsletterRendererProps {
}

interface NewsletterSectionHeader {
    title: string;
    icon: React.ReactNode;
}

const NewsletterSectionHeader: React.FC<NewsletterSectionHeader> = () => {
    return (
        <div className="bg-slate-200 shadow-md rounded-lg mb-4 ml-6 animate-pulse"> {/*Added animate-pulse */}
            <div className="items-center p-4 flex space-x-3">
                <div className="w-6 h-6 rounded-full bg-gray-300 animate-pulse"></div> {/* Placeholder for icon */}
                <div className="w-24 h-4 bg-gray-300 rounded animate-pulse"></div> {/* Placeholder for title */}
            </div>
        </div>
    );
};

const NewsletterRendererSkeleton: React.FC<NewsletterRendererProps> = () => {
    return (
        <div className="p-4 rounded-lg animate-pulse"> {/* Added animate-pulse */}
            <div className="bg-gray-200 shadow-md rounded-lg mb-4 animate-pulse"> {/* Added animate-pulse */}
                <div className="items-center p-4 flex space-x-3">
                    <div className="w-8 h-8 rounded-full bg-gray-300 animate-pulse"></div> {/* Placeholder for logo */}
                    <div className="w-24 h-4 bg-gray-300 rounded animate-pulse"></div> {/* Placeholder for title */}
                </div>
            </div>
            <div className='overflow-y-auto max-h-[600px]'>
                <NewsletterSectionHeader title="Top News" icon={<div className="w-6 h-6 rounded-full bg-gray-300 animate-pulse"></div>} />
                <div className='ml-16'>
                    <div className="grid grid-cols-1 gap-y-4">
                        {[...Array(3)].map((_, index) => (
                            <NewsItemSkeleton key={index} />
                        ))}
                    </div>
                </div>

                <NewsletterSectionHeader title="Podcast" icon={<div className="w-6 h-6 rounded-full bg-gray-300 animate-pulse"></div>} />
                <div className='ml-16'>
                    <div className="grid grid-cols-1 gap-y-4">
                        {[...Array(2)].map((_, index) => (
                            <NewsItemSkeleton key={index} />
                        ))}
                    </div>
                </div>


                <NewsletterSectionHeader title="Regional News" icon={<div className="w-6 h-6 rounded-full bg-gray-300 animate-pulse"></div>} />

                {[...Array(3)].map((_, index) => (
                    <div key={index} className="mb-4 ml-16 animate-pulse">
                        <div className="bg-gray-200 shadow-md rounded-lg mb-4 ">
                            <div className="items-center p-4">
                                <div className="w-24 h-4 bg-gray-300 rounded animate-pulse"></div> {/* Placeholder for region title */}
                            </div>
                        </div>
                        <div className=''>
                            <div className="grid grid-cols-1 gap-y-4">
                                {[...Array(2)].map((_, index) => (
                                    <NewsItemSkeleton key={index} />
                                ))}
                            </div>
                        </div>
                    </div>
                ))}

                <NewsletterSectionHeader title="More Stories" icon={<div className="w-6 h-6 rounded-full bg-gray-300 animate-pulse"></div>} />
                <div className='ml-16'>
                    <div className="grid grid-cols-1 gap-y-4">
                        {[...Array(3)].map((_, index) => (
                            <NewsItemSkeleton key={index} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

const NewsItemSkeleton = () => {
    return (
        <div className="bg-gray-200 shadow-md rounded-lg overflow-hidden mb-4 animate-pulse">
            <div className="flex items-center p-4">
                <div className="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                <div>
                    <div className="w-32 h-4 bg-gray-300 rounded mb-2"></div>
                    <div className="w-48 h-6 bg-gray-300 rounded"></div>
                </div>
            </div>
            <div className="border-t border-gray-200 p-4">
                <div className="inline-flex">
                    <div className="w-24 h-3 bg-gray-300 rounded mr-2"></div>
                    <div className="w-16 h-3 bg-gray-300 rounded"></div>
                </div>
            </div>
        </div>
    );
};

export default NewsletterRendererSkeleton;