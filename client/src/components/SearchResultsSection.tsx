import React from 'react';
import { News } from '../dto/InterfaceDefinition';


interface SearchResultsProps {
    results: News[];
}



const SearchResultsSection: React.FC<SearchResultsProps> = ({ results }) => {
    return (
        <div className="mt-4 flex-grow overflow-y-auto">
            <ul className="list-none pl-6">
                {results.map((result, index) => (
                    <li key={result.url} className="mb-4">
                        <a
                            href={result.url}
                            target="_blank"
                            rel="noopener"
                            className="block hover:bg-gray-100 rounded-md p-4 transition-colors duration-200 ease-in-out"
                        >
                            <div className="flex items-start">
                                <div className="flex items-center mr-4">
                                    <span className="inline-block px-2 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-700 mr-2">
                                        News
                                    </span>
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-gray-800 mb-1">{result.title}</h3>
                                    <p className="text-gray-600 text-sm mb-1">{result.url}</p>
                                    {result.abstract && (
                                        <p className="text-gray-600 text-sm" dangerouslySetInnerHTML={{ __html: result.abstract }} />
                                    )}
                                </div>
                            </div>
                        </a>
                        {index !== results.length - 1 && (
                            <hr className="my-4 border-gray-300" />
                        )}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default SearchResultsSection;
