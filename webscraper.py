from selenium import webdriver
from selenium.webdriver.common.by import By
from resizeimage import resizeimage
import requests
import io
import time
from PIL import Image

PATH = "/Users/adityaramachandran/Desktop/chromedriver"

wd = webdriver.Chrome(PATH)

def get_images_from_google(wd, delay, max_images):
    def scroll_down(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)

    url = "https://www.google.com/search?q=Seneca+White+Deer&tbm=isch&hl=en-GB&chips=q:seneca+white+deer,online_chips:animal:OOT2AjMFhR4%3D&sa=X&ved=2ahUKEwi_joW9iqn7AhVQhNgFHUkuCE8Q4lYoCnoECAEQNw&biw=1200&bih=593"
    wd.get(url)

    image_urls = set()
    skips = 0
    print(max_images)
    while len(image_urls) + skips < max_images:
        print(len(image_urls) + skips)
        scroll_down(wd)
        thumbnails = wd.find_elements(By.CLASS_NAME, "Q4LuWd")
        if len(image_urls) + skips >= max_images:
            break
        for img in thumbnails[len(image_urls) + skips:max_images]:
            try:
                img.click()
                time.sleep(delay)
            except:
                continue

            images = wd.find_elements(By.CLASS_NAME, "n3VNCb")
            for image in images:
                if image.get_attribute('src') in image_urls:
                    max_images += 1
                    skips += 1
                    break

                if image.get_attribute('src') and 'http' in image.get_attribute('src'):
                    image_urls.add(image.get_attribute('src'))
                    print(f"Found {len(image_urls)}")

    return image_urls


def download_image(download_path, url, file_name):
    try:
        image_content = requests.get(url).content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file)
        #image = resizeimage.resize_cover(image, [200, 100
        #image= image.resize((100, 200))
        file_path = download_path + file_name

        with open(file_path,"wb") as f:
            image.save(f,"JPEG")

        print("Done")
    except Exception as e:
        print('FAILED - ', e)
try:
    urls = get_images_from_google(wd, 1, 50)
except KeyboardInterrupt:
    print("Keyboard Interrupt")
for i,url in enumerate(urls):
    download_image("/Users/adityaramachandran/Library/CloudStorage/OneDrive-Personal/Documents/Sem-7/IBM-Project/IBM-Code/Data/Senenca White Deer Mammal/",
                   url, str(301+i) + ".jpg")

wd.quit()
