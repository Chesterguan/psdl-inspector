'use client';

import { useState, useCallback, useRef } from 'react';
import type { PopulationItem } from './PSDLBuilder';
import Tooltip, { GLOSSARY } from './Tooltip';

interface PopulationSectionProps {
  population: {
    include: { conditions: PopulationItem[]; medications: PopulationItem[] };
    exclude: { conditions: PopulationItem[]; medications: PopulationItem[] };
    demographics: { ageMin: number; ageMax: number; sex: string };
  };
  onUpdateItems: (type: 'include' | 'exclude', category: 'conditions' | 'medications', items: PopulationItem[]) => void;
  onUpdateDemographics: (field: string, value: number | string) => void;
}

export default function PopulationSection({ population, onUpdateItems, onUpdateDemographics }: PopulationSectionProps) {
  const [activeTab, setActiveTab] = useState<'include' | 'exclude' | 'demographics'>('include');
  const [searchResults, setSearchResults] = useState<Record<string, PopulationItem[]>>({});
  const [showResults, setShowResults] = useState<Record<string, boolean>>({});
  const searchTimeoutRef = useRef<NodeJS.Timeout>();

  const handleSearch = useCallback(async (query: string, type: 'include' | 'exclude', category: 'conditions' | 'medications') => {
    const key = `${type}-${category}`;

    if (query.length < 2) {
      setShowResults(prev => ({ ...prev, [key]: false }));
      return;
    }

    clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        // Use population search endpoint with type filter
        const vocabType = category === 'conditions' ? 'conditions' : 'medications';
        const endpoint = `http://localhost:8200/api/vocabulary/population/search?q=${encodeURIComponent(query)}&type=${vocabType}&limit=10`;

        const resp = await fetch(endpoint);
        const data = await resp.json();

        if (data.results?.length > 0) {
          setSearchResults(prev => ({ ...prev, [key]: data.results }));
        } else {
          setSearchResults(prev => ({ ...prev, [key]: [] }));
        }
        setShowResults(prev => ({ ...prev, [key]: true }));
      } catch {
        setSearchResults(prev => ({ ...prev, [key]: [] }));
        setShowResults(prev => ({ ...prev, [key]: true }));
      }
    }, 300);
  }, []);

  const selectItem = useCallback((type: 'include' | 'exclude', category: 'conditions' | 'medications', item: PopulationItem, inputElement?: HTMLInputElement) => {
    const key = `${type}-${category}`;
    const current = population[type][category];

    if (!current.some(c => c.concept_id === item.concept_id)) {
      onUpdateItems(type, category, [...current, item]);
    }

    // Clear input after selection
    if (inputElement) {
      inputElement.value = '';
    }

    setShowResults(prev => ({ ...prev, [key]: false }));
  }, [population, onUpdateItems]);

  const removeItem = useCallback((type: 'include' | 'exclude', category: 'conditions' | 'medications', conceptId: number) => {
    const current = population[type][category];
    onUpdateItems(type, category, current.filter(c => c.concept_id !== conceptId));
  }, [population, onUpdateItems]);

  const renderSearchField = (type: 'include' | 'exclude', category: 'conditions' | 'medications', label: string, placeholder: string) => {
    const key = `${type}-${category}`;
    const items = population[type][category];
    const results = searchResults[key] || [];
    const isShowingResults = showResults[key];
    const inputId = `search-${key}`;

    return (
      <div className="form-group mb-4 last:mb-0">
        <label className="form-label block text-sm font-semibold text-foreground-secondary mb-2">{label}</label>

        {/* Selected items as GitHub-style tags */}
        {items.length > 0 && (
          <div className="selected-items flex flex-wrap gap-1.5 mb-2">
            {items.map(item => (
              <span
                key={item.concept_id}
                className="inline-flex items-center gap-1 pl-2.5 pr-1.5 py-0.5 bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 rounded-full text-xs font-medium hover:bg-accent-cyan/25 transition-colors"
              >
                <span className="truncate max-w-[160px]" title={item.concept_name}>
                  {item.concept_name}
                </span>
                <button
                  className="ml-0.5 w-4 h-4 flex items-center justify-center rounded-full hover:bg-accent-cyan/30 text-accent-cyan/70 hover:text-accent-cyan transition-colors"
                  onClick={() => removeItem(type, category, item.concept_id)}
                  title="Remove"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="search-container relative">
          <input
            id={inputId}
            type="text"
            className="search-input w-full px-3 py-2.5 bg-background rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none transition-all placeholder:text-muted/50"
            placeholder={placeholder}
            onInput={(e) => handleSearch((e.target as HTMLInputElement).value, type, category)}
            onBlur={() => setTimeout(() => setShowResults(prev => ({ ...prev, [key]: false })), 200)}
            onFocus={(e) => {
              if ((e.target as HTMLInputElement).value.length >= 2) {
                setShowResults(prev => ({ ...prev, [key]: true }));
              }
            }}
          />
          {isShowingResults && (
            <div className="search-results absolute top-full left-0 right-0 mt-1 bg-background-elevated rounded-lg shadow-lg max-h-[280px] overflow-y-auto z-50 border border-border">
              {results.length > 0 ? (
                results.map(r => (
                  <div
                    key={r.concept_id}
                    className="search-result-item px-3 py-2.5 cursor-pointer hover:bg-background-tertiary transition-colors first:rounded-t-lg last:rounded-b-lg"
                    onClick={() => {
                      const input = document.getElementById(inputId) as HTMLInputElement;
                      selectItem(type, category, r, input);
                    }}
                  >
                    <div className="result-name text-sm font-medium text-foreground">{r.concept_name}</div>
                    <div className="result-meta flex gap-1.5 mt-1">
                      <span className="result-badge font-mono text-xs px-1.5 py-0.5 bg-accent-cyan/10 text-accent-cyan rounded">{r.vocabulary_id}</span>
                      <span className="result-badge font-mono text-xs px-1.5 py-0.5 bg-background-tertiary text-muted rounded">{r.concept_code}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-3 py-2.5 text-muted text-sm italic">No results found</div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="section-panel bg-background-secondary rounded-lg">
      <div className="section-header flex items-center gap-3 px-4 py-3 bg-background-tertiary rounded-t-lg">
        <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">02</span>
        <span className="section-title text-sm font-semibold text-foreground">Target Population</span>
        <Tooltip content={GLOSSARY.population} />
      </div>
      <div className="section-body px-4 py-4">
        {/* Tabs - Underline Style */}
        <div className="tabs flex border-b border-border/50 mb-5">
          {(['include', 'exclude', 'demographics'] as const).map(tab => (
            <button
              key={tab}
              className={`tab-underline px-5 py-2.5 text-xs font-semibold uppercase tracking-wider cursor-pointer transition-all relative ${
                activeTab === tab
                  ? 'text-accent'
                  : 'text-muted hover:text-foreground-secondary'
              }`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
              {activeTab === tab && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Include Tab */}
        {activeTab === 'include' && (
          <div className="tab-content space-y-4">
            {renderSearchField('include', 'conditions', 'Conditions (SNOMED)', 'Search conditions...')}
            {renderSearchField('include', 'medications', 'Medications (RxNorm)', 'Search medications...')}
          </div>
        )}

        {/* Exclude Tab */}
        {activeTab === 'exclude' && (
          <div className="tab-content space-y-4">
            {renderSearchField('exclude', 'conditions', 'Exclude Conditions', 'Search conditions to exclude...')}
            {renderSearchField('exclude', 'medications', 'Exclude Medications', 'Search medications to exclude...')}
          </div>
        )}

        {/* Demographics Tab */}
        {activeTab === 'demographics' && (
          <div className="tab-content space-y-4">
            <div className="form-group">
              <label className="form-label block text-sm font-semibold text-foreground-secondary mb-2">Age Range</label>
              <div className="age-range flex items-center gap-2">
                <input
                  type="number"
                  className="form-input w-16 px-3 py-2.5 bg-background rounded-md text-foreground font-mono text-sm text-center focus:ring-2 focus:ring-accent/30 outline-none"
                  value={population.demographics.ageMin}
                  onChange={(e) => onUpdateDemographics('ageMin', parseInt(e.target.value) || 0)}
                />
                <span className="text-sm text-foreground-secondary">to</span>
                <input
                  type="number"
                  className="form-input w-16 px-3 py-2.5 bg-background rounded-md text-foreground font-mono text-sm text-center focus:ring-2 focus:ring-accent/30 outline-none"
                  value={population.demographics.ageMax}
                  onChange={(e) => onUpdateDemographics('ageMax', parseInt(e.target.value) || 99)}
                />
                <span className="text-sm text-foreground-secondary">years</span>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label block text-sm font-semibold text-foreground-secondary mb-2">Sex</label>
              <select
                className="form-select w-full px-3 py-2.5 bg-background rounded-md text-foreground text-sm cursor-pointer appearance-none focus:ring-2 focus:ring-accent/30 outline-none"
                value={population.demographics.sex}
                onChange={(e) => onUpdateDemographics('sex', e.target.value)}
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%238b949e' d='M2 4l4 4 4-4'/%3E%3C/svg%3E")`,
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'right 12px center',
                  paddingRight: '32px'
                }}
              >
                <option value="any">Any</option>
                <option value="male">Male only</option>
                <option value="female">Female only</option>
              </select>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
