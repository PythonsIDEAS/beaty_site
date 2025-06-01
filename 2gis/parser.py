from bs4 import BeautifulSoup
import json
from datetime import datetime

def parse_reviews(html_file):
    # Load the HTML file
    with open(html_file, encoding='utf-8') as fp:
        soup = BeautifulSoup(fp, 'html.parser')

    # Find all review elements by class
    reviews = soup.find_all(class_=["_1msln3t", "_49x36f", "[data-test-id=review_card]"])
    
    print(f"Total reviews found: {len(reviews)}")
    
    parsed_reviews = []
    
    for review in reviews:
        # Extract author name and info
        author = review.find(class_="_16s5yj3")
        author_name = author.get_text(strip=True) if author else "Anonymous"
        
        # Extract review text
        text_element = review.find(class_="_4mwq3d")
        review_text = text_element.get_text(strip=True) if text_element else ""
        
        # Extract rating (count of filled stars)
        rating = len(review.find_all(class_=["_1fkin5i", "_1156p2j"])) if review else 0
        
        # Extract date
        date_element = review.find(class_="_er2xx9")
        review_date = date_element.get_text(strip=True) if date_element else ""
        
        # Extract additional details if available
        likes = review.find(class_="_er2xx9")
        like_count = likes.get_text(strip=True).split()[0] if likes else "0"
        
        if review_text:  # Only include reviews with actual text content
            review_data = {
                "author": author_name,
                "rating": rating,
                "date": review_date,
                "text": review_text,
                "likes": like_count
            }
            parsed_reviews.append(review_data)
    
    return parsed_reviews

def save_reviews(reviews, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

def print_review_summary(reviews):
    total_reviews = len(reviews)
    total_rating = sum(review['rating'] for review in reviews)
    avg_rating = total_rating / total_reviews if total_reviews > 0 else 0
    
    print(f"\nReview Summary:")
    print(f"Total Reviews: {total_reviews}")
    print(f"Average Rating: {avg_rating:.1f} stars")
    print("\nDetailed Reviews:")
    print("-" * 80)
    
    for idx, review in enumerate(reviews, 1):
        print(f"Review #{idx}")
        print(f"Author: {review['author']}")
        print(f"Rating: {review['rating']} stars")
        print(f"Date: {review['date']}")
        print(f"Likes: {review['likes']}")
        print(f"Text: {review['text']}")
        print("-" * 80)

if __name__ == "__main__":
    input_file = "/Users/tarhanutegenov/beauty_site/2gis/2gis_reviews.html"
    output_file = "2gis/reviews.json"
    
    # Parse reviews from HTML
    reviews = parse_reviews(input_file)
    
    # Save to JSON file
    save_reviews(reviews, output_file)
    
    # Print summary and detailed reviews
    print_review_summary(reviews)
