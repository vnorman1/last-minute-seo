import os
import json
import csv
import io
import re
import urllib.parse
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import validators
import warnings
from urllib.robotparser import RobotFileParser
import time

# SSL figyelmeztetések kikapcsolása
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

app = Flask(__name__)
CORS(app)

class AdvancedSEOAnalyzer:
    def __init__(self, url):
        self.url = url
        self.soup = None
        self.response = None
        self.domain = urllib.parse.urlparse(url).netloc
        self.start_time = None
        
    def fetch_page(self):
        """Weboldal letöltése és BeautifulSoup objektum létrehozása"""
        self.start_time = time.time()
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'hu-HU,hu;q=0.9,en;q=0.8,en-US;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            self.response = session.get(
                self.url, 
                timeout=20,
                verify=False,
                allow_redirects=True,
                stream=False
            )
            self.response.raise_for_status()
            
            if not self.response.content:
                return False, "Üres válasz a szervertől"
            
            # Encoding detection
            self.response.encoding = self.response.apparent_encoding or 'utf-8'
            
            # BeautifulSoup objektum létrehozása
            self.soup = BeautifulSoup(self.response.content, 'html.parser')
            
            if self.soup is None:
                return False, "Nem sikerült feldolgozni a HTML tartalmat"
                
            return True, "Sikeres"
            
        except requests.exceptions.Timeout:
            return False, "Időtúllépés - A weboldal túl lassan válaszol (>20s)"
        except requests.exceptions.ConnectionError:
            return False, "Kapcsolódási hiba - Nem sikerült elérni a weboldalt"
        except requests.exceptions.HTTPError as e:
            return False, f"HTTP hiba: {e.response.status_code} - {e.response.reason}"
        except requests.exceptions.RequestException as e:
            return False, f"Kérés hiba: {str(e)}"
        except Exception as e:
            return False, f"Váratlan hiba: {str(e)}"
    
    def analyze_title(self):
        """Fejlesztett Title tag elemzése"""
        if self.soup is None:
            return {'score': 0, 'title': '', 'length': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        title = self.soup.find('title')
        if not title:
            return {'score': 0, 'title': '', 'length': 0, 'issues': ['Nincs title tag']}
        
        title_text = title.get_text().strip()
        length = len(title_text)
        issues = []
        recommendations = []
        score = 10
        
        if length == 0:
            issues.append('Üres title tag')
            recommendations.append('Adj hozzá leíró címet az oldalhoz')
            score = 0
        elif length < 30:
            issues.append(f'Túl rövid title ({length} karakter < 30)')
            recommendations.append('Bővítsd a címet 30-60 karakter közé')
            score -= 4
        elif length > 60:
            issues.append(f'Túl hosszú title ({length} karakter > 60)')
            recommendations.append('Rövidítsd a címet 60 karakter alá')
            score -= 2
            
        # Keyword density check
        words = title_text.lower().split()
        if len(set(words)) != len(words):
            issues.append('Ismétlődő szavak a title-ben')
            score -= 1
            
        # Brand name check
        if self.domain.replace('www.', '') not in title_text.lower():
            recommendations.append('Fontolja meg a márkanév hozzáadását')
            
        return {
            'score': max(0, score), 
            'title': title_text, 
            'length': length, 
            'issues': issues,
            'recommendations': recommendations,
            'word_count': len(words)
        }
    
    def analyze_meta_description(self):
        """Fejlesztett Meta description elemzése"""
        if self.soup is None:
            return {'score': 0, 'description': '', 'length': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        meta_desc = self.soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
        if not meta_desc:
            return {
                'score': 0, 
                'description': '', 
                'length': 0, 
                'issues': ['Nincs meta description'],
                'recommendations': ['Adj hozzá meta description-t az oldalhoz']
            }
        
        desc_text = meta_desc.get('content', '').strip()
        length = len(desc_text)
        issues = []
        recommendations = []
        score = 10
        
        if length == 0:
            issues.append('Üres meta description')
            recommendations.append('Írj leíró szöveget a meta description-be')
            score = 0
        elif length < 120:
            issues.append(f'Túl rövid meta description ({length} karakter < 120)')
            recommendations.append('Bővítsd 120-160 karakter közé')
            score -= 3
        elif length > 160:
            issues.append(f'Túl hosszú meta description ({length} karakter > 160)')
            recommendations.append('Rövidítsd 160 karakter alá')
            score -= 2
            
        # Call-to-action check
        cta_words = ['kattints', 'látogass', 'tudj meg többet', 'olvass tovább', 'fedezd fel']
        has_cta = any(word in desc_text.lower() for word in cta_words)
        if not has_cta and length > 50:
            recommendations.append('Adj hozzá cselekvésre ösztönző szöveget')
            
        return {
            'score': max(0, score), 
            'description': desc_text, 
            'length': length, 
            'issues': issues,
            'recommendations': recommendations,
            'has_cta': has_cta
        }
    
    def analyze_headings(self):
        """Fejlesztett Heading struktúra elemzése"""
        if self.soup is None:
            return {'score': 0, 'headings': {}, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        headings = {'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []}
        issues = []
        recommendations = []
        score = 10
        
        for level in headings.keys():
            tags = self.soup.find_all(level)
            headings[level] = [tag.get_text().strip() for tag in tags if tag.get_text().strip()]
        
        # H1 ellenőrzés
        if not headings['h1']:
            issues.append('Nincs H1 tag')
            recommendations.append('Adj hozzá egy H1 címsort az oldalhoz')
            score -= 4
        elif len(headings['h1']) > 1:
            issues.append(f'Több H1 tag található ({len(headings["h1"])} db)')
            recommendations.append('Használj csak egy H1 tag-et oldalanként')
            score -= 2
            
        # H1 hossz ellenőrzés
        if headings['h1'] and len(headings['h1'][0]) > 70:
            issues.append('H1 túl hosszú (>70 karakter)')
            recommendations.append('Rövidítsd a H1-et 70 karakter alá')
            score -= 1
            
        # Heading hierarchia ellenőrzés
        total_headings = sum(len(h) for h in headings.values())
        if total_headings < 3:
            issues.append('Kevés heading tag (< 3)')
            recommendations.append('Használj több heading tag-et a jobb struktúráért')
            score -= 2
        elif total_headings > 20:
            issues.append('Túl sok heading tag (> 20)')
            recommendations.append('Csökkentsd a heading tag-ek számát')
            score -= 1
            
        # Heading sorrend ellenőrzés
        if headings['h3'] and not headings['h2']:
            issues.append('H3 van H2 nélkül - rossz hierarchia')
            score -= 1
            
        return {
            'score': max(0, score), 
            'headings': headings, 
            'issues': issues,
            'recommendations': recommendations,
            'total_count': total_headings
        }
    
    def analyze_images(self):
        """Fejlesztett képek elemzése"""
        if self.soup is None:
            return {'score': 0, 'total_images': 0, 'missing_alt': 0, 'empty_alt': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        images = self.soup.find_all('img')
        total_images = len(images)
        missing_alt = 0
        empty_alt = 0
        large_images = 0
        lazy_loading = 0
        issues = []
        recommendations = []
        
        for img in images:
            alt = img.get('alt')
            src = img.get('src', '')
            
            if alt is None:
                missing_alt += 1
            elif alt.strip() == '':
                empty_alt += 1
                
            # Lazy loading check
            if img.get('loading') == 'lazy':
                lazy_loading += 1
                
            # Large image detection (basic)
            if any(keyword in src.lower() for keyword in ['large', 'big', 'full', 'original']):
                large_images += 1
        
        score = 10
        if total_images > 0:
            missing_ratio = (missing_alt + empty_alt) / total_images
            if missing_ratio > 0.5:
                score -= 5
                issues.append(f'{missing_alt + empty_alt}/{total_images} kép alt attribútuma hiányzik vagy üres')
                recommendations.append('Adj hozzá leíró alt szöveget minden képhez')
            elif missing_ratio > 0.2:
                score -= 3
                issues.append(f'{missing_alt + empty_alt}/{total_images} kép alt attribútuma hiányzik vagy üres')
                recommendations.append('Javítsd a hiányzó alt attribútumokat')
                
            # Lazy loading recommendation
            if total_images > 5 and lazy_loading == 0:
                recommendations.append('Használj lazy loading-ot a képekhez')
                
            # Large images warning
            if large_images > 0:
                issues.append(f'{large_images} potenciálisan nagy kép találat')
                recommendations.append('Optimalizáld a képek méretét')
        
        return {
            'score': max(0, score),
            'total_images': total_images,
            'missing_alt': missing_alt,
            'empty_alt': empty_alt,
            'lazy_loading': lazy_loading,
            'large_images': large_images,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_links(self):
        """Fejlesztett linkek elemzése"""
        if self.soup is None:
            return {'score': 0, 'total_links': 0, 'internal_links': 0, 'external_links': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        links = self.soup.find_all('a', href=True)
        internal_links = []
        external_links = []
        broken_links = 0
        nofollow_links = 0
        issues = []
        recommendations = []
        
        for link in links:
            href = link['href']
            rel = link.get('rel', [])
            
            if href.startswith('#'):
                continue  # Skip anchor links
                
            if href.startswith('mailto:') or href.startswith('tel:'):
                continue  # Skip contact links
                
            if href.startswith('http'):
                if self.domain in href:
                    internal_links.append(href)
                else:
                    external_links.append(href)
                    if 'nofollow' in rel:
                        nofollow_links += 1
            elif href.startswith('/'):
                internal_links.append(href)
            elif not href.startswith('javascript:'):
                internal_links.append(href)
        
        score = 10
        
        # Internal links analysis
        if len(internal_links) < 3:
            issues.append('Kevés belső link (< 3)')
            recommendations.append('Adj hozzá több belső linket a jobb navigációért')
            score -= 3
        elif len(internal_links) > 100:
            issues.append('Túl sok belső link (> 100)')
            recommendations.append('Csökkentsd a belső linkek számát')
            score -= 1
            
        # External links analysis
        if len(external_links) > 50:
            issues.append('Túl sok külső link')
            recommendations.append('Csökkentsd a külső linkek számát')
            score -= 1
            
        # Link text analysis (basic)
        generic_texts = ['kattints ide', 'tovább', 'itt', 'link', 'oldalra']
        generic_count = 0
        for link in links:
            link_text = link.get_text().strip().lower()
            if link_text in generic_texts:
                generic_count += 1
                
        if generic_count > 0:
            issues.append(f'{generic_count} általános link szöveg')
            recommendations.append('Használj leíró link szövegeket')
            score -= 1
            
        return {
            'score': max(0, score),
            'total_links': len(links),
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'nofollow_links': nofollow_links,
            'generic_links': generic_count,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_structured_data(self):
        """Fejlesztett strukturált adatok elemzése"""
        if self.soup is None:
            return {'score': 0, 'structured_data': [], 'valid_json_ld': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        structured_data = []
        
        # JSON-LD keresése
        json_scripts = self.soup.find_all('script', type='application/ld+json')
        valid_json_count = 0
        schema_types = set()
        
        for script in json_scripts:
            if script.string:
                try:
                    data = json.loads(script.string.strip())
                    structured_data.append({'type': 'JSON-LD', 'valid': True, 'data': data})
                    valid_json_count += 1
                    
                    # Schema type extraction
                    if isinstance(data, dict) and '@type' in data:
                        schema_types.add(data['@type'])
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and '@type' in item:
                                schema_types.add(item['@type'])
                                
                except json.JSONDecodeError as e:
                    structured_data.append({'type': 'JSON-LD', 'valid': False, 'error': str(e)})
                    issues.append('Érvénytelen JSON-LD struktúra')
                    score -= 3
        
        # Microdata keresése
        microdata = self.soup.find_all(attrs={'itemscope': True})
        if microdata:
            structured_data.append({'type': 'Microdata', 'count': len(microdata)})
        
        # Open Graph tags
        og_tags = self.soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
        if og_tags:
            structured_data.append({'type': 'Open Graph', 'count': len(og_tags)})
        
        # Twitter Cards
        twitter_tags = self.soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
        if twitter_tags:
            structured_data.append({'type': 'Twitter Cards', 'count': len(twitter_tags)})
        
        if not structured_data:
            issues.append('Nincs strukturált adat')
            recommendations.append('Implementálj JSON-LD strukturált adatokat')
            score -= 5
        else:
            if valid_json_count == 0 and not og_tags:
                recommendations.append('Adj hozzá Open Graph tag-eket a social media megosztáshoz')
                
        return {
            'score': max(0, score),
            'structured_data': structured_data,
            'valid_json_ld': valid_json_count,
            'schema_types': list(schema_types),
            'og_tags': len(og_tags) if og_tags else 0,
            'twitter_tags': len(twitter_tags) if twitter_tags else 0,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_performance(self):
        """Fejlesztett teljesítmény elemzés"""
        if self.response is None:
            return {'score': 0, 'page_size_kb': 0, 'load_time_seconds': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        
        # Oldal méret
        page_size = len(self.response.content) / 1024  # KB
        if page_size > 2000:  # 2MB
            issues.append(f'Nagyon nagy oldal méret: {page_size:.1f} KB')
            recommendations.append('Optimalizáld a képeket és tömörítsd a fájlokat')
            score -= 4
        elif page_size > 1000:  # 1MB
            issues.append(f'Nagy oldal méret: {page_size:.1f} KB')
            recommendations.append('Csökkentsd az oldal méretét')
            score -= 2
        
        # Betöltési idő
        load_time = self.response.elapsed.total_seconds()
        if load_time > 5:
            issues.append(f'Nagyon lassú betöltési idő: {load_time:.2f}s')
            recommendations.append('Optimalizáld a szerver válaszidejét')
            score -= 4
        elif load_time > 3:
            issues.append(f'Lassú betöltési idő: {load_time:.2f}s')
            recommendations.append('Javítsd a betöltési sebességet')
            score -= 3
        elif load_time > 1:
            issues.append(f'Közepes betöltési idő: {load_time:.2f}s')
            score -= 1
        
        # HTTP headers analysis
        headers = self.response.headers
        
        # Compression check
        content_encoding = headers.get('Content-Encoding', '')
        if 'gzip' not in content_encoding and 'br' not in content_encoding:
            issues.append('Nincs tömörítés alkalmazva')
            recommendations.append('Engedélyezd a GZIP vagy Brotli tömörítést')
            score -= 1
            
        # Caching headers
        cache_control = headers.get('Cache-Control', '')
        if not cache_control:
            recommendations.append('Adj hozzá cache-control header-eket')
            
        # Security headers
        security_score = 0
        security_headers = ['X-Frame-Options', 'X-Content-Type-Options', 'X-XSS-Protection']
        for header in security_headers:
            if header in headers:
                security_score += 1
                
        if security_score < 2:
            recommendations.append('Implementálj biztonsági header-eket')
        
        return {
            'score': max(0, score),
            'page_size_kb': round(page_size, 1),
            'load_time_seconds': round(load_time, 2),
            'compression': content_encoding or 'Nincs',
            'security_headers': security_score,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_mobile_friendly(self):
        """Fejlesztett mobilbarát elemzés"""
        if self.soup is None:
            return {'score': 0, 'has_viewport': False, 'responsive_images': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        
        # Viewport meta tag
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        has_viewport = viewport is not None
        
        if not has_viewport:
            issues.append('Nincs viewport meta tag')
            recommendations.append('Adj hozzá viewport meta tag-et')
            score -= 5
        else:
            viewport_content = viewport.get('content', '')
            if 'width=device-width' not in viewport_content:
                issues.append('Viewport nem responsive')
                recommendations.append('Használd: width=device-width')
                score -= 2
        
        # Responsive képek
        responsive_images = len(self.soup.find_all('img', attrs={'srcset': True}))
        total_images = len(self.soup.find_all('img'))
        
        if total_images > 5 and responsive_images == 0:
            issues.append('Nincsenek responsive képek')
            recommendations.append('Használj srcset attribútumot a képekhez')
            score -= 2
        
        # Media queries in CSS (basic check)
        style_tags = self.soup.find_all('style')
        has_media_queries = False
        for style in style_tags:
            if '@media' in style.get_text():
                has_media_queries = True
                break
        
        if not has_media_queries:
            recommendations.append('Használj media query-ket a responsive designhoz')
        
        # Mobile-specific meta tags
        mobile_tags = ['apple-mobile-web-app-capable', 'mobile-web-app-capable']
        mobile_optimized = any(self.soup.find('meta', attrs={'name': tag}) for tag in mobile_tags)
        
        return {
            'score': max(0, score),
            'has_viewport': has_viewport,
            'responsive_images': responsive_images,
            'total_images': total_images,
            'has_media_queries': has_media_queries,
            'mobile_optimized': mobile_optimized,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_seo_fundamentals(self):
        """További SEO alapok elemzése"""
        fundamentals = {
            'robots_txt': self.check_robots_txt(),
            'sitemap': self.check_sitemap(),
            'canonical': self.check_canonical(),
            'hreflang': self.check_hreflang(),
            'favicon': self.check_favicon()
        }
        
        score = 0
        total_checks = len(fundamentals)
        
        for check, result in fundamentals.items():
            if result['exists']:
                score += 2
        
        return {
            'score': min(10, score),
            'checks': fundamentals,
            'total_passed': sum(1 for r in fundamentals.values() if r['exists'])
        }
    
    def check_robots_txt(self):
        """Robots.txt ellenőrzése"""
        try:
            robots_url = f"{self.url.rstrip('/')}/robots.txt"
            response = requests.get(robots_url, timeout=5)
            return {
                'exists': response.status_code == 200,
                'url': robots_url,
                'status_code': response.status_code
            }
        except:
            return {'exists': False, 'url': '', 'status_code': 0}
    
    def check_sitemap(self):
        """Sitemap ellenőrzése"""
        sitemaps = [
            f"{self.url.rstrip('/')}/sitemap.xml",
            f"{self.url.rstrip('/')}/sitemap_index.xml"
        ]
        
        for sitemap_url in sitemaps:
            try:
                response = requests.get(sitemap_url, timeout=5)
                if response.status_code == 200:
                    return {
                        'exists': True,
                        'url': sitemap_url,
                        'status_code': response.status_code
                    }
            except:
                continue
                
        return {'exists': False, 'url': '', 'status_code': 0}
    
    def check_canonical(self):
        """Canonical URL ellenőrzése"""
        if self.soup is None:
            return {'exists': False}
            
        canonical = self.soup.find('link', attrs={'rel': 'canonical'})
        return {
            'exists': canonical is not None,
            'url': canonical.get('href') if canonical else ''
        }
    
    def check_hreflang(self):
        """Hreflang ellenőrzése"""
        if self.soup is None:
            return {'exists': False, 'count': 0}
            
        hreflang_tags = self.soup.find_all('link', attrs={'hreflang': True})
        return {
            'exists': len(hreflang_tags) > 0,
            'count': len(hreflang_tags)
        }
    
    def check_favicon(self):
        """Favicon ellenőrzése"""
        if self.soup is None:
            return {'exists': False}
            
        favicon_selectors = [
            'link[rel="icon"]',
            'link[rel="shortcut icon"]',
            'link[rel="apple-touch-icon"]'
        ]
        
        for selector in favicon_selectors:
            if self.soup.select(selector):
                return {'exists': True}
                
        return {'exists': False}
    
    def get_comprehensive_analysis(self):
        """Teljes SEO elemzés végrehajtása"""
        success, message = self.fetch_page()
        if not success:
            return {'error': f'Nem sikerült betölteni a weboldalt: {message}'}
        
        analysis = {
            'url': self.url,
            'domain': self.domain,
            'analyzed_at': datetime.now().isoformat(),
            'title': self.analyze_title(),
            'meta_description': self.analyze_meta_description(),
            'headings': self.analyze_headings(),
            'images': self.analyze_images(),
            'links': self.analyze_links(),
            'structured_data': self.analyze_structured_data(),
            'performance': self.analyze_performance(),
            'mobile_friendly': self.analyze_mobile_friendly(),
            'seo_fundamentals': self.analyze_seo_fundamentals(),
            'content_quality': self.analyze_content_quality(),
            'technical_seo': self.analyze_technical_seo(),
            'social_media_optimization': self.analyze_social_media_optimization(),
            'accessibility_seo': self.analyze_accessibility_seo(),
            'core_web_vitals': self.analyze_core_web_vitals(),
            'local_seo': self.analyze_local_seo(),
            'e_commerce_seo': self.analyze_e_commerce_seo()
        }
        
        # Összpontszám számítása súlyozott átlaggal
        weights = {
            'title': 1.2,
            'meta_description': 1.1,
            'headings': 1.0,
            'images': 0.8,
            'links': 0.9,
            'structured_data': 0.7,
            'performance': 1.3,
            'mobile_friendly': 1.1,
            'seo_fundamentals': 0.9,
            'content_quality': 1.0,
            'technical_seo': 0.9,
            'social_media_optimization': 0.8,
            'accessibility_seo': 0.7,
            'core_web_vitals': 1.2,
            'local_seo': 0.9,
            'e_commerce_seo': 0.8        }
        
        total_weighted_score = 0
        total_weight = 0
        
        for key, weight in weights.items():
            if key in analysis and 'score' in analysis[key]:
                total_weighted_score += analysis[key]['score'] * weight
                total_weight += weight
        
        final_score = total_weighted_score / total_weight if total_weight > 0 else 0
        analysis['total_score'] = round(final_score, 1)
        analysis['grade'] = self.get_grade(analysis['total_score'])
        analysis['analysis_time'] = round(time.time() - self.start_time, 2) if self.start_time else 0
        
        # AI-alapú javaslatok és fejlesztési potenciál
        analysis['seo_recommendations'] = self.generate_seo_recommendations(analysis)
        analysis['improvement_potential'] = self.calculate_seo_improvement_potential(analysis)
        
        return analysis
    
    def get_grade(self, score):
        """Pontszám alapján osztályzat meghatározása"""
        if score >= 9.5:
            return 'A+'
        elif score >= 8.5:
            return 'A'
        elif score >= 7.5:
            return 'A-'
        elif score >= 6.5:
            return 'B+'
        elif score >= 5.5:
            return 'B'
        elif score >= 4.5:
            return 'B-'
        elif score >= 3.5:
            return 'C+'
        elif score >= 2.5:
            return 'C'
        elif score >= 1.5:
            return 'D'
        else:
            return 'F'
    
    def analyze_content_quality(self):
        """Tartalom minőség és SEO relevancia elemzése"""
        if self.soup is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        
        # Szöveg tartalom kinyerése
        text_content = self.soup.get_text(separator=' ', strip=True)
        words = text_content.split()
        word_count = len(words)
        
        # Szó szám ellenőrzés
        if word_count < 300:
            issues.append(f'Kevés szöveges tartalom: {word_count} szó')
            recommendations.append('Adj hozzá legalább 300 szót az oldalhoz')
            score -= 3
        elif word_count < 150:
            issues.append(f'Nagyon kevés tartalom: {word_count} szó')
            recommendations.append('Bővítsd jelentősen a tartalom mennyiségét')
            score -= 5
            
        # Bekezdések elemzése
        paragraphs = self.soup.find_all('p')
        paragraph_count = len([p for p in paragraphs if p.get_text().strip()])
        
        if paragraph_count < 3:
            issues.append(f'Kevés bekezdés: {paragraph_count}')
            recommendations.append('Strukturáld a tartalmat több bekezdésre')
            score -= 2
            
        # Kulcsszó sűrűség elemzés (egyszerű)
        if word_count > 0:
            # A 3 leggyakoribb szó (kivéve stop words)
            stop_words = {'a', 'az', 'és', 'de', 'hogy', 'ez', 'is', 'ki', 'be', 'el', 'fel', 'le', 'meg', 'át'}
            word_freq = {}
            for word in words:
                clean_word = word.lower().strip('.,!?;:()[]{}"\'-')
                if len(clean_word) > 3 and clean_word not in stop_words:
                    word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
                    
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Olvashatóság (átlagos mondat hossz)
            sentences = re.split(r'[.!?]+', text_content)
            avg_sentence_length = word_count / max(len(sentences), 1)
            
            if avg_sentence_length > 25:
                issues.append(f'Hosszú mondatok (átlag: {avg_sentence_length:.1f} szó)')
                recommendations.append('Használj rövidebb mondatokat az olvashatóságért')
                score -= 1
                
        return {
            'score': max(0, score),
            'word_count': word_count,
            'paragraph_count': paragraph_count,
            'avg_sentence_length': avg_sentence_length if 'avg_sentence_length' in locals() else 0,
            'top_keywords': top_words[:3] if 'top_words' in locals() else [],
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_technical_seo(self):
        """Technikai SEO elemzés"""
        if self.soup is None or self.response is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        checks = {}
        
        # HTTPS ellenőrzés
        is_https = self.url.startswith('https://')
        checks['https'] = is_https
        if not is_https:
            issues.append('HTTP protokoll HTTPS helyett')
            recommendations.append('Válts HTTPS-re a biztonság és SEO előnyök miatt')
            score -= 3
            
        # URL struktúra elemzés
        parsed_url = urllib.parse.urlparse(self.url)
        url_path = parsed_url.path
        
        # URL hossz
        if len(self.url) > 100:
            issues.append(f'Hosszú URL: {len(self.url)} karakter')
            recommendations.append('Használj rövidebb, leíró URL-eket')
            score -= 1
            
        # URL speciális karakterek
        if any(char in url_path for char in ['_', '%', '&', '=']):
            issues.append('URL tartalmaz SEO-barátalan karaktereket')
            recommendations.append('Használj kötőjelet és csak alfanumerikus karaktereket')
            score -= 1
            
        # Breadcrumb ellenőrzés
        breadcrumb = self.soup.find('nav', {'aria-label': re.compile(r'breadcrumb', re.I)}) or \
                    self.soup.find(class_=re.compile(r'breadcrumb', re.I))
        checks['breadcrumb'] = bool(breadcrumb)
        if not breadcrumb:
            recommendations.append('Adj hozzá breadcrumb navigációt')
            
        # Internal linking depth
        internal_links = []
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/') or self.domain in href:
                internal_links.append(href)
                
        checks['internal_links_count'] = len(internal_links)
        if len(internal_links) < 3:
            issues.append(f'Kevés belső link: {len(internal_links)}')
            recommendations.append('Növeld a belső linkek számát a jobb navigáció érdekében')
            score -= 2
            
        # Page speed indicators
        render_blocking_resources = []
        
        # CSS files in head
        css_links = self.soup.find_all('link', {'rel': 'stylesheet'})
        for css in css_links:
            if css.get('href'):
                render_blocking_resources.append('CSS: ' + css['href'][:50])
                
        # JS files in head
        head_scripts = self.soup.head.find_all('script', src=True) if self.soup.head else []
        for script in head_scripts:
            render_blocking_resources.append('JS: ' + script['src'][:50])
            
        if len(render_blocking_resources) > 3:
            issues.append(f'Sok render-blocking erőforrás: {len(render_blocking_resources)}')
            recommendations.append('Optimalizáld a CSS/JS betöltést (async, defer)')
            score -= 2
            
        return {
            'score': max(0, score),
            'checks': checks,
            'render_blocking_count': len(render_blocking_resources),
            'render_blocking_resources': render_blocking_resources[:5],
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_social_media_optimization(self):
        """Social Media Optimization (SMO) elemzés"""
        if self.soup is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        
        # Open Graph tags
        og_tags = self.soup.find_all('meta', property=re.compile(r'^og:', re.I))
        og_dict = {tag.get('property', '').lower(): tag.get('content', '') for tag in og_tags}
        
        required_og = ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']
        missing_og = [tag for tag in required_og if tag not in og_dict]
        
        if missing_og:
            issues.append(f'Hiányzó Open Graph tagek: {", ".join(missing_og)}')
            recommendations.append('Adj hozzá Open Graph meta tageket a social sharing-hez')
            score -= len(missing_og)
            
        # Twitter Card tags
        twitter_tags = self.soup.find_all('meta', attrs={'name': re.compile(r'^twitter:', re.I)})
        twitter_dict = {tag.get('name', '').lower(): tag.get('content', '') for tag in twitter_tags}
        
        if not twitter_dict.get('twitter:card'):
            issues.append('Nincs Twitter Card beállítva')
            recommendations.append('Adj hozzá Twitter Card meta tageket')
            score -= 2
            
        # Social media links
        social_links = []
        social_patterns = [
            r'facebook\.com', r'twitter\.com', r'instagram\.com', 
            r'linkedin\.com', r'youtube\.com', r'tiktok\.com'
        ]
        
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            for pattern in social_patterns:
                if re.search(pattern, href, re.I):
                    social_links.append(href)
                    break
                    
        return {
            'score': max(0, score),
            'open_graph_tags': len(og_tags),
            'twitter_tags': len(twitter_tags),
            'social_links': len(set(social_links)),
            'missing_og_tags': missing_og,
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_accessibility_seo(self):
        """Akadálymentesítés és SEO kapcsolat elemzése"""
        if self.soup is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        
        # Language attribute
        html_lang = self.soup.html.get('lang') if self.soup.html else None
        if not html_lang:
            issues.append('Nincs lang attribútum a HTML elemen')
            recommendations.append('Adj hozzá lang="hu" attribútumot a HTML taghez')
            score -= 2
            
        # Heading hierarchy check
        headings = []
        for i in range(1, 7):
            headings.extend([(f'h{i}', tag) for tag in self.soup.find_all(f'h{i}')])
            
        # Check for proper heading order
        heading_levels = [int(h[0][1]) for h in headings]
        if heading_levels:
            prev_level = 0
            for level in heading_levels:
                if level > prev_level + 1:
                    issues.append(f'Ugrás a címsor hierarchiában: H{prev_level} -> H{level}')
                    recommendations.append('Használj folyamatos címsor hierarchiát (H1->H2->H3...)')
                    score -= 1
                    break
                prev_level = level
                
        # Form labels
        forms = self.soup.find_all('form')
        form_issues = 0
        for form in forms:
            inputs = form.find_all(['input', 'textarea', 'select'])
            for inp in inputs:
                inp_id = inp.get('id')
                inp_name = inp.get('name')
                if inp_id:
                    label = form.find('label', {'for': inp_id})
                    if not label:
                        form_issues += 1
                        
        if form_issues > 0:
            issues.append(f'{form_issues} form elem nincs megfelelően címkézve')
            recommendations.append('Használj <label> tageket minden form elemhez')
            score -= min(form_issues, 3)
            
        # Skip links
        skip_link = self.soup.find('a', {'href': re.compile(r'#.*content|#.*main', re.I)})
        if not skip_link:
            recommendations.append('Adj hozzá "skip to main content" linket')
            
        return {
            'score': max(0, score),
            'has_lang_attribute': bool(html_lang),
            'language': html_lang,
            'heading_hierarchy_correct': len(issues) == 0,
            'form_accessibility_issues': form_issues,
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_core_web_vitals(self):
        """Core Web Vitals elemzés (szimulált)"""
        if self.response is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        
        # Page Size elemzés (LCP közelítés)
        page_size_kb = len(self.response.content) / 1024
        
        # Largest Contentful Paint (LCP) becslés
        lcp_estimate = 0.5 + (page_size_kb / 1000)  # Egyszerű becslés
        if lcp_estimate > 4.0:
            issues.append(f'Becsült LCP lassú: {lcp_estimate:.1f}s')
            recommendations.append('Optimalizáld a legnagyobb tartalmi elemeket')
            score -= 4
        elif lcp_estimate > 2.5:
            issues.append(f'Becsült LCP közepes: {lcp_estimate:.1f}s')
            recommendations.append('Javítsd a legnagyobb tartalmi elem betöltési idejét')
            score -= 2
            
        # First Input Delay (FID) - JavaScript elemzés
        script_tags = self.soup.find_all('script')
        js_size = 0
        external_js = 0
        
        for script in script_tags:
            if script.get('src'):
                external_js += 1
            else:
                js_size += len(script.get_text())
                
        if js_size > 100000 or external_js > 10:  # 100KB belső JS vagy 10+ külső JS
            issues.append(f'Sok JavaScript kód: {js_size/1000:.1f}KB + {external_js} külső fájl')
            recommendations.append('Csökkentsd a JavaScript mennyiségét és használj code splitting-et')
            score -= 3
            
        # Cumulative Layout Shift (CLS) - képek és CSS elemzés
        images_without_dimensions = 0
        for img in self.soup.find_all('img'):
            if not (img.get('width') and img.get('height')):
                images_without_dimensions += 1
                
        if images_without_dimensions > 3:
            issues.append(f'{images_without_dimensions} kép nincs méretezve')
            recommendations.append('Adj width és height attribútumokat a képekhez')
            score -= 2
            
        return {
            'score': max(0, score),
            'estimated_lcp': round(lcp_estimate, 2),
            'javascript_size_kb': round(js_size / 1024, 1),
            'external_js_count': external_js,
            'images_without_dimensions': images_without_dimensions,
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_local_seo(self):
        """Helyi SEO elemzés"""
        if self.soup is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        local_signals = {}
        
        # Címkeresés
        text_content = self.soup.get_text().lower()
        
        # Magyar városok és régiók (példa)
        hungarian_cities = [
            'budapest', 'debrecen', 'szeged', 'miskolc', 'pécs', 'győr', 'nyíregyháza',
            'kecskemét', 'székesfehérvár', 'szombathely', 'szolnok', 'tatabánya'
        ]
        
        found_cities = [city for city in hungarian_cities if city in text_content]
        local_signals['cities_mentioned'] = found_cities
        
        # Telefonszám keresés
        phone_pattern = r'(\+36|06)[\s-]?[1-9][\d\s-]{7,9}'
        phones = re.findall(phone_pattern, text_content)
        local_signals['phone_numbers'] = len(phones)
        
        if not phones:
            issues.append('Nincs telefonszám megadva')
            recommendations.append('Adj meg telefonszámot a helyi SEO-hoz')
            score -= 2
            
        # Cím keresés (egyszerű)
        address_keywords = ['utca', 'út', 'tér', 'körút', 'köz', 'sor', 'sétány']
        has_address = any(keyword in text_content for keyword in address_keywords)
        local_signals['has_address'] = has_address
        
        if not has_address:
            recommendations.append('Adj meg teljes címet a jobb helyi SEO-ért')
            
        # Structured data - Local Business
        local_business_schema = False
        json_ld_scripts = self.soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    schema_type = data.get('@type', '')
                    if 'LocalBusiness' in schema_type or 'Organization' in schema_type:
                        local_business_schema = True
                        break
            except:
                continue
                
        local_signals['has_local_business_schema'] = local_business_schema
        
        if not local_business_schema:
            issues.append('Nincs Local Business schema')
            recommendations.append('Adj hozzá LocalBusiness structured data-t')
            score -= 3
            
        return {
            'score': max(0, score),
            'local_signals': local_signals,
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_e_commerce_seo(self):
        """E-commerce specifikus SEO elemzés"""
        if self.soup is None:
            return {'score': 0, 'issues': ['Nem sikerült betölteni az oldalt']}
            
        score = 10
        issues = []
        recommendations = []
        ecommerce_signals = {}
        
        # Termék indikátorok keresés
        product_indicators = [
            'ár', 'vásárlás', 'kosár', 'szállítás', 'termék', 'bolt', 'shop',
            'webshop', 'áruház', 'kedvezmény', 'akció', 'ft', 'forint'
        ]
        
        text_content = self.soup.get_text().lower()
        found_indicators = [indicator for indicator in product_indicators if indicator in text_content]
        ecommerce_signals['product_indicators'] = len(found_indicators)
        
        # Ár megjelenítés
        price_patterns = [
            r'\d+[\s.]?\d*\s*ft',
            r'\d+[\s.]?\d*\s*forint',
            r'\d+[\s.]?\d*\s*huf',
            r'\d+[\s,]\d{3}'
        ]
        
        has_prices = any(re.search(pattern, text_content, re.I) for pattern in price_patterns)
        ecommerce_signals['has_prices'] = has_prices
        
        # Product schema
        product_schema = False
        json_ld_scripts = self.soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    schema_type = data.get('@type', '')
                    if 'Product' in schema_type or 'Offer' in schema_type:
                        product_schema = True
                        break
            except:
                continue
                
        ecommerce_signals['has_product_schema'] = product_schema
        
        if len(found_indicators) > 3 and not product_schema:
            issues.append('E-commerce jellegű oldal Product schema nélkül')
            recommendations.append('Adj hozzá Product és Offer schema markup-ot')
            score -= 3
            
        # Breadcrumb e-commerce specifikus
        breadcrumb = self.soup.find('nav', {'aria-label': re.compile(r'breadcrumb', re.I)})
        if len(found_indicators) > 5 and not breadcrumb:
            issues.append('E-commerce oldalon nincs breadcrumb navigáció')
            recommendations.append('Implementálj breadcrumb navigációt a kategóriákhoz')
            score -= 2
            
        return {
            'score': max(0, score),
            'ecommerce_signals': ecommerce_signals,
            'issues': issues,
            'recommendations': recommendations
        }

    def analyze_competitor_keywords(self, competitor_urls=None):
        """Konkurencia kulcsszó elemzés (egyszerű verzió)"""
        if not competitor_urls:
            return {'score': 10, 'message': 'Nincs konkurencia URL megadva'}
            
        # Itt lehetne implementálni a konkurencia elemzést
        # Placeholder a jövőbeli fejlesztéshez
        return {
            'score': 10,
            'message': 'Konkurencia elemzés még nem implementált',
            'suggestions': ['Implementáld a competitor analysis modult']
        }

    def generate_seo_recommendations(self, analysis_results):
        """AI-alapú SEO javaslatok generálása"""
        all_issues = []
        all_recommendations = []
        priority_recommendations = []
        
        # Összes probléma és javaslat összegyűjtése
        for module_name, module_data in analysis_results.items():
            if isinstance(module_data, dict):
                if 'issues' in module_data:
                    all_issues.extend(module_data['issues'])
                if 'recommendations' in module_data:
                    all_recommendations.extend(module_data['recommendations'])
        
        # Prioritás alapú rendezés
        high_priority_keywords = ['title', 'meta', 'h1', 'https', 'mobile']
        medium_priority_keywords = ['image', 'link', 'performance', 'schema']
        
        for rec in all_recommendations:
            rec_lower = rec.lower()
            if any(keyword in rec_lower for keyword in high_priority_keywords):
                priority_recommendations.append(('HIGH', rec))
            elif any(keyword in rec_lower for keyword in medium_priority_keywords):
                priority_recommendations.append(('MEDIUM', rec))
            else:
                priority_recommendations.append(('LOW', rec))
        
        # Top 10 legfontosabb javaslat
        priority_recommendations.sort(key=lambda x: ['HIGH', 'MEDIUM', 'LOW'].index(x[0]))
        
        return {
            'total_issues': len(all_issues),
            'total_recommendations': len(all_recommendations),
            'top_priority_recommendations': priority_recommendations[:10],
            'quick_wins': [rec for priority, rec in priority_recommendations if priority == 'HIGH'][:5],
            'summary': f"{len(all_issues)} probléma és {len(all_recommendations)} javaslat azonosítva"
        }

    def calculate_seo_improvement_potential(self, analysis_results):
        """SEO fejlesztési potenciál kalkulátor"""
        current_scores = {}
        max_possible_scores = {}
        improvement_potential = {}
        
        for module_name, module_data in analysis_results.items():
            if isinstance(module_data, dict) and 'score' in module_data:
                current_score = module_data['score']
                max_score = 10  # Minden modul max 10 pont
                
                current_scores[module_name] = current_score
                max_possible_scores[module_name] = max_score
                improvement_potential[module_name] = max_score - current_score
        
        total_current = sum(current_scores.values())
        total_max = sum(max_possible_scores.values())
        total_improvement = sum(improvement_potential.values())
        
        improvement_percentage = (total_improvement / total_max * 100) if total_max > 0 else 0
        
        # Top 3 legnagyobb fejlesztési terület
        top_improvements = sorted(
            improvement_potential.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        return {
            'current_total_score': round(total_current, 1),
            'maximum_possible_score': total_max,
            'improvement_potential_points': round(total_improvement, 1),
            'improvement_percentage': round(improvement_percentage, 1),
            'top_improvement_areas': top_improvements,
            'estimated_score_after_fixes': round(total_current + (total_improvement * 0.8), 1)  # 80% sikeres javítást feltételezve
        }

# Global változó az utolsó elemzés tárolásához
current_analysis_data = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_url():
    global current_analysis_data
    
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL megadása kötelező'}), 400
    
    # URL normalizálása
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if not validators.url(url):
        return jsonify({'error': 'Érvénytelen URL formátum'}), 400
    
    try:
        analyzer = AdvancedSEOAnalyzer(url)
        analysis = analyzer.get_comprehensive_analysis()
        
        if 'error' in analysis:
            return jsonify(analysis), 500
        
        # Tárolás exportáláshoz
        current_analysis_data = analysis
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': f'Elemzési hiba: {str(e)}'}), 500

@app.route('/export/<format>')
def export_analysis(format):
    global current_analysis_data
    
    if current_analysis_data is None:
        return jsonify({'error': 'Nincs elérhető elemzési adat'}), 400
    
    if format == 'csv':
        # Részletes CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'URL', 'Domain', 'Elemzés Ideje', 'Összpontszám', 'Osztályzat',
            'Title Score', 'Title Length', 'Title Text',
            'Meta Desc Score', 'Meta Desc Length', 
            'Headings Score', 'H1 Count', 'Total Headings',
            'Images Score', 'Total Images', 'Missing Alt',
            'Links Score', 'Internal Links', 'External Links',
            'Structured Data Score', 'Valid JSON-LD', 'Schema Types',
            'Performance Score', 'Page Size (KB)', 'Load Time (s)',
            'Mobile Score', 'Has Viewport', 'Responsive Images',
            'SEO Fundamentals Score', 'Robots.txt', 'Sitemap',
            'Content Quality Score', 'Word Count', 'Paragraph Count',
            'Technical SEO Score', 'HTTPS', 'Breadcrumb',
            'Social Media Optimization Score', 'Open Graph Tags', 'Twitter Tags',
            'Accessibility SEO Score', 'Lang Attribute', 'Form Accessibility Issues',
            'Analysis Time (s)'
        ])
        
        # Data row
        writer.writerow([
            current_analysis_data.get('url', ''),
            current_analysis_data.get('domain', ''),
            current_analysis_data.get('analyzed_at', ''),
            current_analysis_data.get('total_score', 0),
            current_analysis_data.get('grade', ''),
            current_analysis_data.get('title', {}).get('score', 0),
            current_analysis_data.get('title', {}).get('length', 0),
            current_analysis_data.get('title', {}).get('title', ''),
            current_analysis_data.get('meta_description', {}).get('score', 0),
            current_analysis_data.get('meta_description', {}).get('length', 0),
            current_analysis_data.get('headings', {}).get('score', 0),
            len(current_analysis_data.get('headings', {}).get('headings', {}).get('h1', [])),
            current_analysis_data.get('headings', {}).get('total_count', 0),
            current_analysis_data.get('images', {}).get('score', 0),
            current_analysis_data.get('images', {}).get('total_images', 0),
            current_analysis_data.get('images', {}).get('missing_alt', 0),
            current_analysis_data.get('links', {}).get('score', 0),
            current_analysis_data.get('links', {}).get('internal_links', 0),
            current_analysis_data.get('links', {}).get('external_links', 0),
            current_analysis_data.get('structured_data', {}).get('score', 0),
            current_analysis_data.get('structured_data', {}).get('valid_json_ld', 0),
            ', '.join(current_analysis_data.get('structured_data', {}).get('schema_types', [])),
            current_analysis_data.get('performance', {}).get('score', 0),
            current_analysis_data.get('performance', {}).get('page_size_kb', 0),
            current_analysis_data.get('performance', {}).get('load_time_seconds', 0),
            current_analysis_data.get('mobile_friendly', {}).get('score', 0),
            current_analysis_data.get('mobile_friendly', {}).get('has_viewport', False),
            current_analysis_data.get('mobile_friendly', {}).get('responsive_images', 0),
            current_analysis_data.get('seo_fundamentals', {}).get('score', 0),
            current_analysis_data.get('seo_fundamentals', {}).get('checks', {}).get('robots_txt', {}).get('exists', False),
            current_analysis_data.get('seo_fundamentals', {}).get('checks', {}).get('sitemap', {}).get('exists', False),
            current_analysis_data.get('content_quality', {}).get('score', 0),
            current_analysis_data.get('content_quality', {}).get('word_count', 0),
            current_analysis_data.get('content_quality', {}).get('paragraph_count', 0),
            current_analysis_data.get('technical_seo', {}).get('score', 0),
            current_analysis_data.get('technical_seo', {}).get('checks', {}).get('https', False),
            current_analysis_data.get('technical_seo', {}).get('render_blocking_count', 0),
            current_analysis_data.get('social_media_optimization', {}).get('score', 0),
            current_analysis_data.get('social_media_optimization', {}).get('open_graph_tags', 0),
            current_analysis_data.get('social_media_optimization', {}).get('twitter_tags', 0),
            current_analysis_data.get('accessibility_seo', {}).get('score', 0),
            current_analysis_data.get('accessibility_seo', {}).get('has_lang_attribute', False),
            current_analysis_data.get('accessibility_seo', {}).get('form_accessibility_issues', 0),
            current_analysis_data.get('analysis_time', 0)
        ])
        
        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8-sig'))
        mem.seek(0)
        
        return send_file(
            mem,
            as_attachment=True,
            download_name=f'seo_analysis_detailed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mimetype='text/csv'
        )
    
    return jsonify({'error': 'Nem támogatott formátum'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0')
