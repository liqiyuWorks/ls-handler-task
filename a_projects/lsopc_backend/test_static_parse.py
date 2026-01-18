#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uvicorn
import logging
from lxml import etree
from playwright.sync_api import sync_playwright
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Dynamic XPath Parser API",
    description="API to extract data from dynamic webpages using XPath and Playwright.",
    version="1.0.0"
)

class ParseRequest(BaseModel):
    url: str = Field(default="https://data.eastmoney.com/report", description="Target website URL")
    xpath: str = Field(default="//*[@id='indexnewreport_table']/table/tbody/tr[1]/td[5]", description="XPath expression to extract data")

class ParseResponse(BaseModel):
    status: str
    count: int
    results: List[str]

class XpathAnalyzer:
    def __init__(self):
        pass

    def fetch_and_parse(self, url, xpath_expression) -> List[str]:
        """Fetch the URL content using Playwright and parse with XPath."""
        results = []
        with sync_playwright() as p:
            # Launch browser
            logging.info("Launching browser...")
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                logging.info(f"Navigating to: {url}")
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Check for XPath validity before waiting
                try:
                    logging.info(f"Waiting for element matching: {xpath_expression}")
                    # Convert generic xpath to a playwright selector
                    page.wait_for_selector(f"xpath={xpath_expression}", timeout=10000)
                except Exception as e:
                    logging.warning(f"Wait for selector failed or timed out: {e}")

                # Get the full HTML content after JS execution
                content = page.content()
                browser.close()
                
                # Parse with lxml
                results = self._parse_html(content, xpath_expression)
                
            except Exception as e:
                logging.error(f"Browser interaction failed: {e}")
                # We might want to raise here or return empty, depends on requirement.
                # For now, let's log and return what we have (or empty).
                if 'browser' in locals():
                    browser.close()
                raise e
            
        return results

    def _parse_html(self, content, xpath_expression) -> List[str]:
        """Parse content using lxml XPath."""
        try:
            parser = etree.HTMLParser(encoding='utf-8')
            selector = etree.HTML(content, parser=parser)
            
            if selector is None:
                logging.error("Failed to create HTML selector.")
                return []

            raw_results = selector.xpath(xpath_expression)
            
            clean_results = []
            for result in raw_results:
                 if isinstance(result, etree._Element):
                    # Get raw HTML content
                    # method="html" is explicit for HTML serialization, though default usually works well for elements.
                    # encoding="unicode" ensures we get a string back.
                    html_content = etree.tostring(result, encoding="unicode").strip()
                    if html_content:
                        clean_results.append(html_content)
                 else:
                    # Strings, numbers, etc.
                    clean_results.append(str(result).strip())
            
            return clean_results
            
        except Exception as e:
            logging.error(f"Error during parsing: {e}")
            return []

analyzer = XpathAnalyzer()

@app.post("/api/parse", response_model=ParseResponse, summary="Parse URL with XPath")
def parse_endpoint(request: ParseRequest):
    """
    Fetches the given URL using a headless browser (Playwright) and extracts data using the provided XPath.
    
    - **url**: The target website URL (e.g., https://data.eastmoney.com/report/)
    - **xpath**: The XPath expression to extract data (e.g., //table//tr/td[1])
    """
    if not request.url or not request.xpath:
        raise HTTPException(status_code=400, detail="URL and XPath are required")
        
    try:
        data = analyzer.fetch_and_parse(request.url, request.xpath)
        return ParseResponse(
            status="success",
            count=len(data),
            results=data
        )
    except Exception as e:
        logging.error(f"API Error: {e}")
        # Return error response or raise 500
        # If we raise 500, the response_model is skipped usually, but let's be clean.
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
