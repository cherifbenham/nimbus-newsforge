import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SearchResponse } from '../dto/InterfaceDefinition';
import ApiHelper from '../backend/ApiHelper';
import { motion } from 'framer-motion'
import SearchResultsSkeletton from '../components/skeletons/SearchResultSkeleton';
import SearchResultsSection from '../components/SearchResultsSection';
import Pagination from '../components/Pagination';
import { marked } from 'marked';


const RESULTS_PER_PAGE = 10;

const SearchResults = () => {
    const [, setShowSearchResults] = useState(false);
    const [searchResponse, setSearchResponse] = useState<SearchResponse>();
    const [isLoading, setIsLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');

    const [searchParams,] = useSearchParams();



    useEffect(() => {
        setSearchQuery(searchParams.get('query') || '');
        setCurrentPage(1);
        setShowSearchResults(true);
    }, [searchParams]);



    useEffect(() => {
        if (searchQuery) {
            setCurrentPage(1);
            setShowSearchResults(true);
        }
    }, [searchQuery]);


    useEffect(() => {
        if (searchQuery) {
            fetchSearchResults();
        }
    }, [searchQuery, currentPage]);



    const fetchSearchResults = async () => {
        setIsLoading(true);
        try {
            const validatedResponse = await ApiHelper.searchNews(searchQuery);
            setSearchResponse(validatedResponse);
        } catch (error) {
            console.error('Error fetching search results:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handlePageChange = (value: number) => {
        setCurrentPage(value); // Update currentPage when pagination changes
    };

    const renderSummary = () => {
        if (searchResponse?.summary) {
            const html = marked.parse(searchResponse.summary);
            return (
                <div className="prose prose-lg dark:prose-invert max-w-3xl"> {/* Added prose classes */}
                    <div dangerouslySetInnerHTML={{ __html: html }} />
                </div>
            );
        } else {
            return <p className="text-gray-500">No summary available.</p>;
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="bg-gray-100 min-h-screen"
        >
            <div className="container mx-auto p-4">



                <article className="bg-blue-100  text-wrap p-4 rounded-md shadow-md mb-8">
                    <div className="flex items-center space-x-2">
                        <img className="w-5 h-5" src="/spark.png" alt="logo" />
                        <h6 className="text-xs font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-red-500 flex items-center"> {/* Add flex items-center */}
                            Gemini AI Summarization
                        </h6>
                    </div>
                    {renderSummary()}
                </article>


                {
                    isLoading ? (
                        <div className="flex justify-center">
                            <SearchResultsSkeletton />
                        </div>
                    ) : (
                        <>


                            <div className="mb-2">
                                <p className="text-gray-600 text-sm">
                                    {searchResponse?.totalsize} results
                                </p>
                                <h3 className="text-lg font-medium">
                                    Showing results for: <span className="font-bold">{searchQuery}</span>
                                </h3>
                            </div>

                            {searchResponse && (
                                <div className='flex flex-col justify-center'>
                                    <SearchResultsSection results={searchResponse.results} />
                                    {searchResponse.totalsize > RESULTS_PER_PAGE && (
                                        <div className="flex justify-center mt-3">
                                            <Pagination
                                                currentPage={currentPage}
                                                totalPages={Math.ceil(searchResponse.totalsize / RESULTS_PER_PAGE)}
                                                onPageChange={handlePageChange}
                                            />

                                        </div>
                                    )}

                                </div>
                            )}
                        </>
                    )
                }
            </div>
        </motion.div>
    );
};
export default SearchResults;


