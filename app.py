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
            'seo_fundamentals': self.analyze_seo_fundamentals()
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
            'seo_fundamentals': 0.9
        }
        
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
