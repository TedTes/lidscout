/**
 * Type definitions for business data.
 * Following Single Responsibility Principle - only defines types.
 */

export interface Business {
    name: string;
    phone?: string | null;
    email?: string | null;
    address?: string | null;
    website?: string | null;
    rating?: number | null;
    reviews_count?: number | null;
  }
  
  export interface SearchCriteria {
    industry: string;
    location: string;
    radius_km?: number;
    max_results?: number;
  }
  
  export interface SearchResponse {
    query: string;
    total_results: number;
    businesses: Business[];
  }