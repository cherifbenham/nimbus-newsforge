import React from 'react';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
}

const Pagination: React.FC<PaginationProps> = ({ currentPage, totalPages, onPageChange }) => {
    const handlePageClick = (page: number) => {
        onPageChange(page);
    };

    const MAX_VISIBLE_PAGES = 5; // Adjust as needed

    // Logic for displaying page numbers
    const visiblePages = [];
    if (totalPages <= MAX_VISIBLE_PAGES) {
        // Show all pages if there are less than MAX_VISIBLE_PAGES
        for (let i = 1; i <= totalPages; i++) {
            visiblePages.push(i);
        }
    } else {
        // Show ellipsis and limit visible pages
        if (currentPage <= 3) {
            // Show first 3 pages and ellipsis
            for (let i = 1; i <= 3; i++) {
                visiblePages.push(i);
            }
            visiblePages.push('...');
            visiblePages.push(totalPages - 1);
            visiblePages.push(totalPages);
        } else if (currentPage >= totalPages - 2) {
            // Show last 3 pages and ellipsis
            visiblePages.push(1);
            visiblePages.push(2);
            visiblePages.push('...');
            for (let i = totalPages - 2; i <= totalPages; i++) {
                visiblePages.push(i);
            }
        } else {
            // Show 3 pages around the current page and ellipsis
            visiblePages.push(1);
            visiblePages.push(2);
            visiblePages.push('...');
            for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                visiblePages.push(i);
            }
            visiblePages.push('...');
            visiblePages.push(totalPages - 1);
            visiblePages.push(totalPages);
        }
    }

    return (
        <nav className="flex justify-center mt-4">

            <ul className="flex items-center space-x-2">

                <li>
                    <button
                        onClick={() => handlePageClick(currentPage - 1)}
                        disabled={currentPage === 1}
                        className="flex items-center  justify-center  duration-150 rounded-full"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="size-5 fill-google-blue-light">
                            <path fillRule="evenodd" d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z" clipRule="evenodd" />
                        </svg>



                    </button>

                </li>

                {/* Page Number Buttons */}
                {visiblePages.map((page, index) => (
                    <li key={index}>
                        {typeof page === 'number' ? (
                            <button
                                onClick={() => handlePageClick(page)}
                                className={`
                  ${page === currentPage
                                        ? 'w-10 h-10 bg-customer-blue text-white font-medium rounded-full text-sm'
                                        : 'w-10 h-10 text-google-blue-light transition-colors duration-150 rounded-full focus:shadow-outline hover:bg-google-blue-light hover:text-white'}
                `}
                            >
                                <span className="flex items-center justify-center w-full h-full"> {/* Center the number */}
                                    {page}
                                </span>
                            </button>
                        ) : (
                            <span className="text-gray-400 font-medium px-3 py-2 text-sm">...</span>
                        )}
                    </li>
                ))}

                {/* Next Button */}
                <li>
                    <button
                        onClick={() => handlePageClick(currentPage + 1)}
                        disabled={currentPage === totalPages}
                        className="flex items-center justify-center text-gray-600 transition-colors duration-150 rounded-full focus:shadow-outline hover:bg-gray-300"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="size-5 fill-google-blue-light">
                            <path fillRule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                        </svg>



                    </button>
                </li>
            </ul>
        </nav>
    );
};

export default Pagination;