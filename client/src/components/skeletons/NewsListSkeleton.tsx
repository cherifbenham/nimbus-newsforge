import React from 'react';
import { NewsListTitle } from "../NewsList"

interface NewsItemSkeletonProps { }

const NewsItemSkeleton: React.FC<NewsItemSkeletonProps> = () => {
    return (
        <div className="bg-gray-200 shadow-md rounded-lg overflow-hidden mb-4 animate-pulse"> {/* Added animate-pulse */}
            <div className="flex items-center p-4">
                <div className="w-12 h-12 bg-gray-300 rounded-full mr-4"></div> {/* Placeholder for image/icon */}
                <div>
                    <div className="w-32 h-4 bg-gray-300 rounded mb-2"></div> {/* Placeholder for title */}
                    <div className="w-48 h-6 bg-gray-300 rounded"></div> {/* Placeholder for abstract */}
                </div>
            </div>
            <div className="border-t border-gray-200 p-4">
                <div className="inline-flex">
                    <div className="w-24 h-3 bg-gray-300 rounded mr-2"></div> {/* Placeholder for source */}
                    <div className="w-16 h-3 bg-gray-300 rounded"></div> {/* Placeholder for date */}
                </div>
            </div>
        </div>
    );
};

const NewsListSkeleton: React.FC<{ numberOfItems: number }> = ({ numberOfItems }) => {
    return (
        <div className="p-4 rounded-lg">
            <NewsListTitle />
            <div className="max-h-[700px] overflow-y-auto">
                {[...Array(numberOfItems)].map((_, index) => (
                    <NewsItemSkeleton key={index} />
                ))}
            </div>
        </div>
    );
};

export default NewsListSkeleton;