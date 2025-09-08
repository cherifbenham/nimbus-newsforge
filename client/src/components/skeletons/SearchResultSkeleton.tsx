const SearchResultsSkeletton: React.FC = () => {

    return (
        <div className="mt-4 animate-pulse w-full"> {/* Add animate-pulse class */}
            <ul className="list-none pl-6">
                <li className="mb-4">
                    <div className="block rounded-md p-4">
                        <div className="flex items-start w-full">
                            <div className="flex items-center mr-4">
                                <span className="inline-block px-2 py-1 w-12 rounded-full text-xs font-bold bg-gray-300 text-gray-700 mr-2">

                                </span>
                            </div>
                            <div className="w-full">
                                <div className="h-4 bg-gray-300 rounded-full w-1/3 mb-2"></div> {/* Title */}
                                <div className="h-2 bg-gray-200 rounded-full w-1/2 mb-2"></div> {/* URL */}
                                <div className="h-3 bg-gray-200 rounded-full w-3/5"></div> {/* Snippet */}
                            </div>
                        </div>
                    </div>
                    <hr className="my-4 border-gray-300" /> {/* Divider */}
                </li>
                <li className="mb-4">
                    <div className="block rounded-md p-4">
                        <div className="flex items-start">
                            <div className="flex items-center mr-4">
                                <span className="inline-block px-2 py-1  w-12 rounded-full text-xs font-bold bg-gray-300 text-gray-700 mr-2">
                                    {/* ... */}
                                </span>
                            </div>
                            <div className="w-full">
                                <div className="h-4 bg-gray-300 rounded-full w-1/3 mb-2"></div> {/* Title */}
                                <div className="h-2 bg-gray-200 rounded-full w-1/2 mb-2"></div> {/* URL */}
                                <div className="h-3 bg-gray-200 rounded-full w-3/5"></div> {/* Snippet */}
                            </div>
                        </div>
                    </div>
                    <hr className="my-4 border-gray-300" /> {/* Divider */}
                </li>
                <li className="mb-4">
                    <div className="block rounded-md p-4">
                        <div className="flex items-start">
                            <div className="flex items-center mr-4">
                                <span className="inline-block px-2 py-1 w-12  rounded-full text-xs font-bold bg-gray-300 text-gray-700 mr-2">
                                    {/* ... */}
                                </span>
                            </div>
                            <div className="w-full">
                                <div className="h-4 bg-gray-300 rounded-full w-1/3 mb-2"></div> {/* Title */}
                                <div className="h-2 bg-gray-200 rounded-full w-1/2 mb-2"></div> {/* URL */}
                                <div className="h-3 bg-gray-200 rounded-full w-3/5"></div> {/* Snippet */}
                            </div>
                        </div>
                    </div>
                    <hr className="my-4 border-gray-300" /> {/* Divider */}
                </li>
            </ul>
        </div>
    )

}

export default SearchResultsSkeletton;