import React, { useEffect, useState } from 'react';
import axios from 'axios';
import config from '../config/apiService';

const Setup: React.FC = () => {
  const [prompt, setPrompt] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<string>('');

  useEffect(() => {
    const fetchPrompt = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`${config.url.API_URL}/compose-weekly/prompt`);
        setPrompt(res.data.prompt || '');
      } catch (e) {
        setStatus('Failed to load prompt');
      } finally {
        setLoading(false);
      }
    };
    fetchPrompt();
  }, []);

  const handleSave = async () => {
    try {
      setLoading(true);
      await axios.put(`${config.url.API_URL}/compose-weekly/prompt`, { prompt });
      setStatus('Saved');
      setTimeout(() => setStatus(''), 1500);
    } catch (e) {
      setStatus('Save failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-100">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">Compose Weekly Setup</h1>
          <p className="text-sm text-gray-600 dark:text-slate-300">
            Configure how Gemini generates CI comments for news items. These instructions guide the AI to produce insightful,
            data-driven analysis tailored to Amadeus's competitive intelligence needs.
          </p>
        </header>

        <section className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold mb-2">System Prompt Instructions</h2>
            <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">
              Define additional context and guidance for Gemini. This is appended to the default system prompt and helps
              the AI understand what's relevant to Amadeus and how to generate meaningful comments.
            </p>
          </div>

          <div className="space-y-2">
            <label htmlFor="prompt-textarea" className="block text-sm font-medium">
              Custom Instructions (Markdown supported)
            </label>
            <textarea
              id="prompt-textarea"
              className="w-full min-h-[400px] p-4 rounded-md border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 font-mono text-sm"
              placeholder={`# Custom CI Analysis Instructions

## Company Context
Amadeus is a leading travel technology company providing IT solutions to airlines, hotels, travel agencies, and other travel providers through its Global Distribution System (GDS) and technology platforms.

### Key Business Areas
- **GDS & Distribution**: Airline reservations, hotel bookings, car rentals
- **IT Solutions**: Airline reservation systems, departure control, revenue management
- **Payment & Merchandising**: Payment processing, ancillary revenue optimization
- **Travel Seller Solutions**: Agency booking tools, corporate travel management

### Primary Competitors
- **Sabre**: Direct GDS competitor, airline IT provider
- **Travelport**: GDS competitor (owned by Farelogix)
- **Google Travel**: Growing threat in distribution and search
- **Accelya**: Payment and revenue accounting competitor

### Key Markets & Customers
- **Airlines**: Our largest customer segment (reservation systems, revenue management)
- **Travel Agencies & OTAs**: Use our GDS for booking (Booking.com, Expedia, CTMs)
- **Hotels**: Distribution via GDS, property management systems
- **Ground Transportation**: Emerging segment

## CI Comment Guidelines

### What to Extract
1. **Specific Metrics**: Revenue figures, growth rates, market share, customer counts
2. **Strategic Moves**: M&A, partnerships, product launches, market entries/exits
3. **Technology Trends**: AI/ML adoption, new distribution channels, payment innovations
4. **Financial Health**: Profitability, funding rounds, valuation changes
5. **Market Dynamics**: Regional growth, capacity changes, demand patterns

### How to Write Comments
- **Be data-driven**: Lead with numbers and facts
- **Show impact**: Explain what it means for Amadeus (opportunity or threat)
- **Compare when possible**: YoY changes, regional differences, vs competitors
- **Avoid generic statements**: No "this is interesting" or "relevant development"
- **Keep concise**: 1-3 sentences maximum

### Examples of GOOD Comments ✅
- "All regions operating above winter 2019 capacity levels, except South-East Asia. North America and Europe expected to grow 2.1% and 4.6% respectively."
- "Sabre claims airlines can achieve up to a 3.5% uplift in overall revenue."
- "While Navan improved financial performance, it continues to operate at a loss. For fiscal year ending January 2025, posted net loss of $18M vs previous year's $331.5M loss."

### Examples of BAD Comments ❌
- "Interesting development in travel technology"
- "This could impact our business"
- "Will Agentic AI Turn OTAs Into Passive Order Takers?" (just repeating title)

## Classification Priorities
- **Competitors**: News about Sabre, Travelport, Google Travel, Accelya
- **Travel Providers**: Airlines, OTAs, hotels, agencies (our customers)
- **M&A & Investments**: Consolidation affecting market structure
- **Technology**: AI, distribution channels, payment systems
- **Financial Reports**: Quarterly results, funding rounds, valuations`}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <p className="text-xs text-gray-500 dark:text-slate-400">
              💡 Tip: Include company context, relevant competitors, key metrics to track, and examples of good vs bad comments.
            </p>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-slate-700">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSave}
                disabled={loading}
                className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 font-medium"
              >
                {loading ? 'Saving...' : 'Save Instructions'}
              </button>
              {status && (
                <span className={`text-sm font-medium ${status.includes('failed') || status.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                  {status}
                </span>
              )}
            </div>
            <button
              onClick={() => setPrompt('')}
              className="px-4 py-2 rounded-md border border-gray-300 dark:border-slate-600 hover:bg-gray-100 dark:hover:bg-slate-700 text-sm"
            >
              Clear
            </button>
          </div>
        </section>

        <section className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 p-4">
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">How This Works</h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-disc list-inside">
            <li>Your instructions are stored in Firestore and loaded when analyzing news items</li>
            <li>They are appended to the base system prompt that defines Gemini's role as a CI analyst</li>
            <li>The AI uses both the base prompt and your custom instructions to generate comments</li>
            <li>Changes take effect immediately for new analysis requests</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default Setup;
