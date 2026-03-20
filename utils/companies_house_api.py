"""
Companies House API Integration Module for LiquidRound

This module provides functionality to interact with the UK Companies House API
to retrieve company information, directors, and persons with significant control (PSCs).
"""

import requests
import json
import time
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CompanyProfile:
    """Data class for company profile information"""
    company_number: str
    company_name: str
    company_status: str
    incorporation_date: Optional[str]
    company_type: str
    sic_codes: List[str]
    registered_address: Dict[str, str]
    business_activity: Optional[str] = None

@dataclass
class Officer:
    """Data class for company officer information"""
    officer_id: str
    name: str
    role: str
    appointed_on: Optional[str]
    resigned_on: Optional[str]
    nationality: Optional[str]
    occupation: Optional[str]
    country_of_residence: Optional[str]

@dataclass
class PSC:
    """Data class for Person with Significant Control"""
    psc_id: str
    name: str
    psc_type: str  # individual, corporate-entity, legal-person
    nature_of_control: List[str]
    notified_on: Optional[str]
    country_of_residence: Optional[str]
    nationality: Optional[str]

class CompaniesHouseAPI:
    """
    Companies House API client for retrieving UK company information
    """
    
    def __init__(self, api_key: str, use_sandbox: bool = False):
        """
        Initialize the Companies House API client
        
        Args:
            api_key (str): Your Companies House API key
            use_sandbox (bool): Whether to use sandbox environment
        """
        self.api_key = api_key
        self.use_sandbox = use_sandbox
        
        if use_sandbox:
            self.base_url = "https://api-sandbox.company-information.service.gov.uk"
        else:
            self.base_url = "https://api.company-information.service.gov.uk"
        self.session = requests.Session()
        self.session.auth = (api_key, '')  # Basic auth with API key as username
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'LiquidRound-Business-Search/1.0'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """Implement basic rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to the Companies House API
        
        Args:
            endpoint (str): API endpoint
            params (dict): Query parameters
            
        Returns:
            dict: API response data or None if error
        """
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def search_companies(self, query: str, items_per_page: int = 20) -> List[Dict]:
        """
        Search for companies by name
        
        Args:
            query (str): Company name to search for
            items_per_page (int): Number of results per page
            
        Returns:
            list: List of company search results
        """
        params = {
            'q': query,
            'items_per_page': items_per_page
        }
        
        response = self._make_request('/search/companies', params)
        if response and 'items' in response:
            return response['items']
        return []
    
    def get_company_profile(self, company_number: str) -> Optional[CompanyProfile]:
        """
        Get detailed company profile
        
        Args:
            company_number (str): Company registration number
            
        Returns:
            CompanyProfile: Company profile data or None
        """
        response = self._make_request(f'/company/{company_number}')
        if not response:
            return None
        
        # Extract SIC codes and business activity
        sic_codes = []
        business_activity = None
        
        if 'sic_codes' in response:
            sic_codes = response['sic_codes']
        
        # Try to get business activity from various fields
        if 'business_activity' in response:
            business_activity = response['business_activity']
        elif sic_codes:
            business_activity = f"SIC codes: {', '.join(sic_codes)}"
        
        return CompanyProfile(
            company_number=response.get('company_number', ''),
            company_name=response.get('company_name', ''),
            company_status=response.get('company_status', ''),
            incorporation_date=response.get('date_of_creation'),
            company_type=response.get('type', ''),
            sic_codes=sic_codes,
            registered_address=response.get('registered_office_address', {}),
            business_activity=business_activity
        )
    
    def get_officers(self, company_number: str) -> List[Officer]:
        """
        Get company officers (directors, secretaries, etc.)
        
        Args:
            company_number (str): Company registration number
            
        Returns:
            list: List of Officer objects
        """
        response = self._make_request(f'/company/{company_number}/officers')
        if not response or 'items' not in response:
            return []
        
        officers = []
        for item in response['items']:
            officer = Officer(
                officer_id=item.get('links', {}).get('officer', {}).get('appointments', '').split('/')[-2] if item.get('links', {}).get('officer', {}).get('appointments') else '',
                name=item.get('name', ''),
                role=item.get('officer_role', ''),
                appointed_on=item.get('appointed_on'),
                resigned_on=item.get('resigned_on'),
                nationality=item.get('nationality'),
                occupation=item.get('occupation'),
                country_of_residence=item.get('country_of_residence')
            )
            officers.append(officer)
        
        return officers
    
    def get_pscs(self, company_number: str) -> List[PSC]:
        """
        Get Persons with Significant Control (Ultimate Beneficial Owners)
        
        Args:
            company_number (str): Company registration number
            
        Returns:
            list: List of PSC objects
        """
        response = self._make_request(f'/company/{company_number}/persons-with-significant-control')
        if not response or 'items' not in response:
            return []
        
        pscs = []
        for item in response['items']:
            # Determine PSC type and extract ID
            psc_type = 'individual'
            psc_id = ''
            
            if 'kind' in item:
                if 'corporate-entity' in item['kind']:
                    psc_type = 'corporate-entity'
                elif 'legal-person' in item['kind']:
                    psc_type = 'legal-person'
            
            # Extract PSC ID from links
            if 'links' in item and 'self' in item['links']:
                psc_id = item['links']['self'].split('/')[-1]
            
            psc = PSC(
                psc_id=psc_id,
                name=item.get('name', ''),
                psc_type=psc_type,
                nature_of_control=item.get('natures_of_control', []),
                notified_on=item.get('notified_on'),
                country_of_residence=item.get('country_of_residence'),
                nationality=item.get('nationality')
            )
            pscs.append(psc)
        
        return pscs
    
    def get_company_network(self, company_name: str, max_companies: int = 10) -> Dict[str, Any]:
        """
        Build a network of related companies based on shared directors and PSCs
        
        Args:
            company_name (str): Starting company name
            max_companies (int): Maximum number of companies to include
            
        Returns:
            dict: Network data with nodes and edges
        """
        network = {
            'nodes': [],
            'edges': [],
            'metadata': {
                'search_query': company_name,
                'timestamp': datetime.now().isoformat(),
                'total_companies': 0,
                'total_people': 0
            }
        }
        
        # Search for the main company
        companies = self.search_companies(company_name, items_per_page=max_companies)
        if not companies:
            return network
        
        processed_companies = set()
        processed_people = set()
        
        for company_data in companies[:max_companies]:
            company_number = company_data.get('company_number')
            if not company_number or company_number in processed_companies:
                continue
            
            # Get detailed company information
            profile = self.get_company_profile(company_number)
            if not profile:
                continue
            
            # Add company node
            company_node = {
                'id': f"company_{company_number}",
                'label': profile.company_name,
                'type': 'Company',
                'company_number': company_number,
                'status': profile.company_status,
                'incorporation_date': profile.incorporation_date,
                'sic_codes': profile.sic_codes,
                'business_activity': profile.business_activity,
                'size': 20,
                'color': '#1f77b4'
            }
            network['nodes'].append(company_node)
            processed_companies.add(company_number)
            
            # Get officers
            officers = self.get_officers(company_number)
            for officer in officers:
                person_id = f"person_{officer.name.replace(' ', '_').lower()}"
                
                if person_id not in processed_people:
                    # Add person node
                    person_node = {
                        'id': person_id,
                        'label': officer.name,
                        'type': 'Person',
                        'role': officer.role,
                        'nationality': officer.nationality,
                        'occupation': officer.occupation,
                        'size': 15,
                        'color': '#ff7f0e'
                    }
                    network['nodes'].append(person_node)
                    processed_people.add(person_id)
                
                # Add relationship edge
                edge = {
                    'source': person_id,
                    'target': f"company_{company_number}",
                    'relationship': f"DIRECTOR_OF",
                    'role': officer.role,
                    'appointed_on': officer.appointed_on
                }
                network['edges'].append(edge)
            
            # Get PSCs
            pscs = self.get_pscs(company_number)
            for psc in pscs:
                psc_id = f"psc_{psc.name.replace(' ', '_').lower()}"
                
                if psc_id not in processed_people:
                    # Add PSC node
                    psc_node = {
                        'id': psc_id,
                        'label': psc.name,
                        'type': 'PSC',
                        'psc_type': psc.psc_type,
                        'nationality': psc.nationality,
                        'country_of_residence': psc.country_of_residence,
                        'size': 18,
                        'color': '#2ca02c'
                    }
                    network['nodes'].append(psc_node)
                    processed_people.add(psc_id)
                
                # Add control relationship
                edge = {
                    'source': psc_id,
                    'target': f"company_{company_number}",
                    'relationship': 'CONTROLS',
                    'nature_of_control': psc.nature_of_control,
                    'notified_on': psc.notified_on
                }
                network['edges'].append(edge)
        
        # Update metadata
        network['metadata']['total_companies'] = len([n for n in network['nodes'] if n['type'] == 'Company'])
        network['metadata']['total_people'] = len([n for n in network['nodes'] if n['type'] in ['Person', 'PSC']])
        
        return network

def get_sic_code_description(sic_code: str) -> str:
    """
    Get description for SIC code (simplified mapping)
    """
    sic_descriptions = {
        '70100': 'Activities of head offices',
        '64191': 'Banks',
        '64209': 'Other credit granting',
        '68100': 'Buying and selling of own real estate',
        '68209': 'Other letting and operating of own or leased real estate',
        '70229': 'Management consultancy activities other than financial management',
        '82990': 'Other business support service activities n.e.c.'
    }
    return sic_descriptions.get(sic_code, f"SIC Code: {sic_code}")
