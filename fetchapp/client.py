from base64 import b64encode
from urllib.parse import urlencode
import urllib.request, urllib.error, urllib.parse
from datetime import datetime
from lxml import etree
from dateutil.parser import parse

class FetchAppOrderException(Exception):
    """Raised when an order fails."""
    pass

class FetchAppAuthenticationException(Exception):
    """Raised when authentication fails."""
    pass


class FetchAppRequestException(Exception):
    """Raised when a request fails with an error message."""
    pass

class FetchAppInvalidOrderTypeException(Exception):
    """
    Raised when an unsupported order type is passed to
    the orders methods.
    """
    pass

class InvalidHTTPRequestTypeException(Exception):
    """
    Raised when an unsupported http request type is made.
    """
    pass

class FetchApp(object):
    """
    Support for the FetchApp API.
    http://www.fetchapp.com/pages/help-api
    """

    host = "app.fetchapp.com"

    def __init__(self, key, token):
        self.key = key
        self.token = token
    
    def account_create(self, name, first_name, last_name, email, url):
        """Create a new account"""
        
        account = etree.Element("account")
        etree.SubElement(account, "name").text = str(name)
        etree.SubElement(account, "first_name").text = str(first_name)
        etree.SubElement(account, "last_name").text = str(last_name)
        etree.SubElement(account, "email").text = str(email)
        etree.SubElement(account, "url").text = str(url)
        request = urllib.request.Request(
            "http://%s%s" % (self.host, '/api/account/create'), 
            data=etree.tostring(account, encoding="utf-8", xml_declaration=True))
        request.add_header('Content-Type', "application/xml")
        xmldoc = self._make_request(request)
        return self._deserialize(xmldoc)   

    def account(self):
        """Information about your account."""
        
        path = "/api/account"
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)

    def new_token(self):
        """Generate a new API token (this replaces your existing one)"""
        
        path = "/api/new_token"
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)
        
    def downloads(self, per_page=None, page=None):
        """List your downloads"""
        
        path = "/api/downloads"
        parameters = {}
        if per_page is not None:
            parameters["per_page"] = int(per_page)
        if page is not None:
            parameters["page"] = int(page)
        xmldoc = self._call(path, parameters=parameters)
        return self._deserialize(xmldoc)        
    
    def items(self, per_page=None, page=None, sku=None):
        """List your items"""
        
        path = "/api/items"
        if sku is not None:
            path = "%s/:%s" % (path, sku)
        parameters = {}
        if per_page is not None:
            parameters["per_page"] = int(per_page)
        if page is not None:
            parameters["page"] = int(page)
        xmldoc = self._call(path, parameters=parameters)
        return self._deserialize(xmldoc)

    def item_details(self, sku):
        """List details of a specified item"""
        
        path = "/api/items/%s" % sku
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)
    
    def item_delete(self, sku):
        """Delete a specified item"""
        
        path = "/api/items/%s/delete" % sku
        xmldoc = self._call(path, method="delete")
        return self._deserialize(xmldoc) == "Ok."
    
    def item_create(self, sku, name, price):
        """Create a specified item"""
        
        path = "/api/items/create"
        item = etree.Element("item")
        etree.SubElement(item, "sku").text = str(sku)
        etree.SubElement(item, "name").text = str(name)
        etree.SubElement(item, "price", attrib={"type":"float"}).text = str(price)
        xmldoc = self._call(
            path, 
            data=etree.tostring(item, encoding="utf-8", xml_declaration=True), 
            method="post",
            content_type="application/xml")
        return self._deserialize(xmldoc)
    
    def item_update(self, sku, new_sku=None, name=None, price=None):
        """Update a specified item"""
        
        path = "/api/items/%s" % sku
        item = etree.Element("item")
        if new_sku is not None:
            etree.SubElement(item, "sku").text = str(new_sku)
        if name is not None:
            etree.SubElement(item, "name").text = str(name)
        if price is not None:
            etree.SubElement(item, "price", attrib={"type":"float"}).text = str(price)
        xmldoc = self._call(    
            path, 
            data=etree.tostring(item, encoding="utf-8", xml_declaration=True), 
            method="put",
            content_type="application/xml")
        return self._deserialize(xmldoc)        
    
    def item_list_files(self, sku):
        """List all the files for an item."""
        
        path = "/api/items/%s/files" % sku
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)       

    def item_list_downloads(self, sku):
        """List all the downloads for an item"""
        
        path = "/api/items/%s/downloads" % sku
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)
    
    def orders(self):
        """List all your orders"""
        
        path = "/api/orders"
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)       
    
    def order_details(self, order_id):
        """Details of a specified order"""
        
        path = "/api/orders/%s" % order_id
        xmldoc = self._call(path)
        return self._deserialize(xmldoc)        
    
    def order_delete(self, order_id):
        """Delete a specified order"""
        
        path = "/api/orders/%s/delete" % order_id
        xmldoc = self._call(path, method="delete")
        return self._deserialize(xmldoc) == "Ok."

    def order_expire(self, order_id):
        """Expire a specified order"""
        
        path = "/api/orders/%s/expire" % order_id
        xmldoc = self._call(path, method="post")
        return self._deserialize(xmldoc) == "Ok."

    def order_send_email(self, order_id):
        """Send download email of a specified order"""
        
        path = "/api/orders/%s/send_email" % order_id
        xmldoc = self._call(path, method="post")
        return self._deserialize(xmldoc) == "Ok."
        
    def _order_xmldoc(self, 
            order_id=None, 
            new_order_id=None,
            title=None,
            first_name=None,
            last_name=None,
            email=None,
            skus=None,
            expiration_date=None,
            send_email=None,
            download_limit=None,
            ignore_items=None):
        """Create an order"""

        order = etree.Element("order")
        if order_id is not None:
            etree.SubElement(order, "id").text = str(order_id)
        if title is not None:
            etree.SubElement(order, "title").text = str(title)
        if first_name is not None:
            etree.SubElement(order, "first_name").text = str(first_name)
        if last_name is not None:
            etree.SubElement(order, "last_name").text = str(last_name)
        if email is not None:
            etree.SubElement(order, "email").text = str(email)
        if send_email is not None:
            send_email = int(send_email)
            etree.SubElement(order, "send_email").text = str(send_email)
        if ignore_items is not None:
            ignore_items = int(ignore_items)
            etree.SubElement(order, "ignore_items").text = str(ignore_items)
        if expiration_date is not None:
            if not isinstance(expiration_date, datetime):
                expiration_date = parse(expiration_date)
            ed_subelement = etree.SubElement(
                order, 
                "expiration_date", 
                attrib={"type":"datetime"})
            ed_subelement.text = expiration_date.isoformat()
        if download_limit is not None:
            dl_subelement = etree.SubElement(
                order, 
                "download_limit", 
                attrib={"type":"integer"})
            dl_subelement.text = str(download_limit)
        if skus is not None:
            if not isinstance(skus, list):
                raise FetchAppOrderException("skus must be a list")
            order_items = etree.SubElement(
                order, 
                "order_items", 
                attrib={"type":"array"})
            for sku in skus:
                order_item = etree.SubElement(order_items, "order_item")
                etree.SubElement(order_item, "sku").text = str(sku)
        return order

    def order_create(self, 
            order_id, 
            title,
            first_name,
            last_name,
            email,
            skus,
            expiration_date=None,
            send_email=None,
            download_limit=None,
            ignore_items=None):
        """Create an order"""
        
        path = "/api/orders/create"
        if not isinstance(skus, list):
            raise FetchAppOrderException("skus must be a list")
        order = self._order_xmldoc(
            order_id=order_id, 
            title=title,
            first_name=first_name,
            last_name=last_name,
            email=email,
            skus=skus,
            expiration_date=expiration_date,
            send_email=send_email,
            download_limit=download_limit,
            ignore_items=ignore_items)
        xmldoc = self._call(
            path, 
            data=etree.tostring(order, encoding="utf-8", xml_declaration=True),
            method="post",
            content_type="application/xml")
        return self._deserialize(xmldoc)
        
    def order_update(self,
            order_id=None, 
            title=None,
            first_name=None,
            last_name=None,
            email=None,
            skus=None,
            expiration_date=None,
            send_email=None,
            download_limit=None,
            ignore_items=None):
        """Update a specified order"""
        
        path = "/api/orders/%s/update" % (order_id)
        order = self._order_xmldoc(
            title=title,
            first_name=first_name,
            last_name=last_name,
            email=email,
            skus=skus,
            expiration_date=expiration_date,
            send_email=send_email,
            download_limit=download_limit,
            ignore_items=ignore_items)
        xmldoc = self._call(
            path, 
            data=etree.tostring(order, encoding="utf-8", xml_declaration=True),
            method="put",
            content_type="application/xml")
        return self._deserialize(xmldoc)
    
    def uploads(self, per_page=None, page=None):
        """List your uploads"""
        
        path = "/api/uploads"
        parameters = {}
        if per_page is not None:
            parameters["per_page"] = int(per_page)
        if page is not None:
            parameters["page"] = int(page)
        xmldoc = self._call(path, parameters=parameters)
        return self._deserialize(xmldoc)
    
    def _deserialize(self, xmldoc):
        if "type" in xmldoc.attrib:
            type = xmldoc.attrib["type"]
            if type == "array":
                data = []
                for child in xmldoc:
                    data.append(self._deserialize(child))
                return data
            else:
                if xmldoc.text is None:
                    return None
                elif type == "datetime":
                    return parse(xmldoc.text)
                elif type == "float":
                    return float(xmldoc.text)
                elif type == "integer":
                    return int(xmldoc.text)
        else:
            if len(xmldoc) == 0:
                return xmldoc.text
            else:
                data = {}
                for child in xmldoc:
                    data[child.tag] = self._deserialize(child)
            return data
        
    def _call(self, path, parameters=None, data=None, method="get", content_type=None):
        method = method.upper()
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            raise InvalidHTTPRequestTypeException(method.upper())
        if parameters is not None:
            url = "http://%s%s?%s" % (self.host, path, urlencode(parameters))
        else:
            url = "http://%s%s" % (self.host, path)
        request = urllib.request.Request(url, data=data)
        request.add_header('Authorization', 
            'Basic %s' % b64encode("%s:%s" % (self.key, self.token)))
        if content_type is not None:
            request.add_header('Content-Type', content_type)
        if method in ["PUT", "DELETE"]:
            request.get_method = lambda: method
        return self._make_request(request)
        
    def _make_request(self, request):
        opener = urllib.request.build_opener(urllib.request.HTTPHandler)
        try:
            response = opener.open(request)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise FetchAppAuthenticationException()
            elif e.code == 404:
                raise e
            else:
                response_string = e.read()
                message = None
                try:
                    xmldoc = etree.fromstring(response_string)
                    if xmldoc.tag == "message": 
                        message = xmldoc.text
                except:
                    raise e
                if message is not None:
                    raise FetchAppRequestException(message)
                else:
                    raise e
        root = etree.fromstring(response.read())
        return root