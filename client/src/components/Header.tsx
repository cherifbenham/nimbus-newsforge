import NavigationHeader from "./NavigationMenu";
import SearchBar from "./SearchBar"


const Header = () => {
    return (
        <div className="bg-customer-blue flex items-center">
            <img className="h-4 mx-4" src='/amadeus-logo-dark-sky.png' alt='logo' />
            <NavigationHeader />
            <SearchBar />
        </div>
    );
};

export default Header