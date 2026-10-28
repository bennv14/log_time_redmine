import unittest
from io import BytesIO
from app import app as flask_app

class TestCsvValidation(unittest.TestCase):
    def setUp(self) -> None:
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    def test_upload_empty_csv(self) -> None:
        data = {'file': (BytesIO(b""), 'empty.csv')}
        resp = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Tệp CSV trống", resp.get_json()["error"])

    def test_upload_missing_no_column(self) -> None:
        csv_content = "Col1,Col2,Col3\n1,2,3"
        data = {'file': (BytesIO(csv_content.encode('utf-8')), 'invalid.csv')}
        resp = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        self.assertIn("không tìm thấy cột 'No'", resp.get_json()["error"])

    def test_upload_invalid_task_id(self) -> None:
        csv_content = (
            ",No,Task,Task URL,Task Effort,4/1\n"
            ",1,Invalid Task,https://redmine.jprep.jp/invalid,1,1\n"
        )
        data = {'file': (BytesIO(csv_content.encode('utf-8')), 'invalid_task.csv')}
        resp = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("validationErrors", data)
        self.assertTrue(any("URL công việc không chứa ID Redmine" in e for e in data["validationErrors"]))

    def test_upload_non_numeric_hours(self) -> None:
        csv_content = (
            ",No,Task,Task URL,Task Effort,4/1\n"
            ",1,Task 1,https://redmine.jprep.jp/redmine/issues/1,1,abc\n"
        )
        data = {'file': (BytesIO(csv_content.encode('utf-8')), 'non_numeric.csv')}
        resp = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("validationErrors", data)
        self.assertTrue(any("Giá trị không phải số" in e for e in data["validationErrors"]))

    def test_upload_negative_hours(self) -> None:
        csv_content = (
            ",No,Task,Task URL,Task Effort,4/1\n"
            ",1,Task 1,https://redmine.jprep.jp/redmine/issues/1,1,-5\n"
        )
        data = {'file': (BytesIO(csv_content.encode('utf-8')), 'negative.csv')}
        resp = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("validationErrors", data)
        self.assertTrue(any("Giờ không được âm" in e for e in data["validationErrors"]))

    def test_upload_hours_over_24(self) -> None:
        csv_content = (
            ",No,Task,Task URL,Task Effort,4/1\n"
            ",1,Task 1,https://redmine.jprep.jp/redmine/issues/1,25,25\n"
        )
        data = {'file': (BytesIO(csv_content.encode('utf-8')), 'over_24.csv')}
        resp = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("validationErrors", data)
        self.assertTrue(any("Giờ vượt quá 24h" in e for e in data["validationErrors"]))

if __name__ == "__main__":
    unittest.main()
