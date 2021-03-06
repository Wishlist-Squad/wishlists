# Copyright 2016, 2019 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Wishlist Service

Paths:
------
GET /wishlists - Returns a list all of the Wishlists
GET /wishlists/{id} - Returns the wishlists with a given id number
POST /wishlists - creates a new wishlists record in the database
PUT /wishlists/{id} - updates a wishlists record in the database
DELETE /wishlists/{id} - deletes a wishlists record in the database
"""

import os
import sys
import logging
from flask import Flask, jsonify, request, url_for, make_response, abort
from flask_restx import Api, Resource, fields, reqparse, inputs
from . import status  # HTTP Status Codes
from werkzeug.exceptions import NotFound

# For this example we'll use SQLAlchemy, a popular ORM that supports a
# variety of backends including SQLite, MySQL, and PostgreSQL
from flask_sqlalchemy import SQLAlchemy
from service.models import Product, Wishlist, DataValidationError

# Import Flask application
from . import app

######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    app.logger.info("Request for Root URL")
    return app.send_static_file("index.html")
    # data = '{name: <string>, category: <string>}'
    # url = request.base_url + 'pets' # url_for('list_pets')
    # return jsonify(name='Pet Demo REST API Service', version='1.0', url=url, data=data), status.HTTP_200_OK


######################################################################
# Configure Swagger before initializing it
######################################################################
api = Api(app,
          version='1.0.0',
          title='Wishlist REST API Service',
          description='This is a server for the Wishlist service.',
          default='wishlists',
          default_label='Wishlist Service',
          doc='/apidocs', # default also could use doc='/apidocs/'
          prefix='/'
         )


# Define the model so that the docs reflect what can be sent
create_product_model = api.model('Product', {
    'item_id': fields.Integer(required=True, description="The ID of the product"),
    "name": fields.String(required=True, description="The name of the product")
})

product_model = api.inherit(
    'ProductModel',
    create_product_model,
    {
        'wishlist_id': fields.Integer(required=True, description="The wishlist this item belongs to"),
        'id': fields.Integer(readOnly=True, description="The unique id assigned to each item in a wishlist"),
        "purchased": fields.Boolean(required=False, description="Whether this item was purchased off of this wishlist") 
    }
)

create_model = api.model('Wishlist', {
    'name': fields.String(required=True,
                          description='The name of the Wishlist'),
    'customer_id': fields.Integer(required=True,
                              description='The associated customer for this wishlist'),
})

wishlist_model = api.inherit(
    'WishlistModel', 
    create_model,
    {
        'id': fields.Integer(readOnly=True,
                            description='The unique id assigned internally by service'),
        'products': fields.List(fields.Nested(product_model))
    }
)

wishlist_args = reqparse.RequestParser()
wishlist_args.add_argument('customer_id', type=int, location="args", required=False, help='List Wishlists by customer')

######################################################################
# Special Error Handlers
######################################################################
# @api.errorhandler(DataValidationError)
# def request_validation_error(error):
#     """ Handles Value Errors from bad data """
#     message = str(error)
#     app.logger.error(message)
#     return {
#         'status_code': status.HTTP_400_BAD_REQUEST,
#         'error': 'Bad Request',
#         'message': message
#     }, status.HTTP_400_BAD_REQUEST


######################################################################
#  PATH: /wishlists/{id}
######################################################################
@api.route('/wishlists/<int:wishlist_id>')
@api.param('wishlist_id', 'The Wishlist identifier')
class WishlistResource(Resource):
    """
    WishlistResource class

    Allows the manipulation of a single Wishlist
    GET /wishlist{id} - Returns a Wishlist with the id
    PUT /wishlist{id} - Update a Wishlist with the id
    DELETE /wishlist{id} -  Deletes a Wishlist with the id
    """

    #------------------------------------------------------------------
    # RETRIEVE A WISHLIST
    #------------------------------------------------------------------
    @api.doc('get_wishlists')
    @api.response(404, 'Wishlist not found')
    @api.marshal_with(wishlist_model)
    def get(self, wishlist_id):
        """
        Retrieve a single Wishlist

        This endpoint will return a Wishlist based on it's id
        """
        app.logger.info("Request to Retrieve a wishlist with id [%s]", wishlist_id)
        wishlist = Wishlist.find(wishlist_id)
        if not wishlist:
            abort(status.HTTP_404_NOT_FOUND, "Wishlist with id '{}' was not found.".format(wishlist_id))
        return wishlist.serialize(), status.HTTP_200_OK

    #------------------------------------------------------------------
    # UPDATE AN EXISTING WISHLIST
    #------------------------------------------------------------------
    @api.doc('update_wishlists')
    @api.response(415, 'Unsupported media type')
    @api.response(404, 'Wishlist not found')
    @api.response(400, 'The posted Wishlist data was not valid')
    @api.expect(wishlist_model, validate=True)
    @api.marshal_with(wishlist_model)
    def put(self, wishlist_id):
        """
        Update a Wishlist

        This endpoint will update a Wishlist based the body that is posted
        """
        app.logger.info('Request to Update a wishlist with id [%s]', wishlist_id)
        check_content_type("application/json")
        wishlist = Wishlist.find(wishlist_id)
        if not wishlist:
            abort(status.HTTP_404_NOT_FOUND, "404 Not Found: Wishlist with id '{}' was not found.".format(wishlist_id))
        app.logger.debug('Payload = %s', api.payload)
        data = api.payload
        updated_wishlist = Wishlist()
        updated_wishlist.deserialize(data)
        wishlist.name = updated_wishlist.name
        wishlist.customer_id = updated_wishlist.customer_id
        wishlist.id = wishlist_id
        wishlist.save()

        app.logger.info("Wishlist with ID [%s] updated.", wishlist.id)
        return wishlist.serialize(), status.HTTP_200_OK

    #------------------------------------------------------------------
    # DELETE A WISHLIST
    #------------------------------------------------------------------
    @api.doc('delete_wishlists')
    @api.response(204, 'Wishlist deleted')
    def delete(self, wishlist_id):
        """
        Delete a Wishlist

        This endpoint will delete a Wishlist based the id specified in the path
        """
        app.logger.info('Request to Delete a wishlist with id [%s]', wishlist_id)
        wishlist = Wishlist.find(wishlist_id)
        if wishlist:
            wishlist.delete()
            app.logger.info('Wishlist with id [%s] was deleted', wishlist_id)

        return '', status.HTTP_204_NO_CONTENT

######################################################################
#  PATH: /wishlists
######################################################################
@api.route('/wishlists', strict_slashes=False)
class WishlistCollection(Resource):
    """ Handles all interactions with collections of Wishlists """
    #------------------------------------------------------------------
    # LIST ALL WISHLISTS
    #------------------------------------------------------------------
    @api.doc('list_wishlists')
    @api.expect(wishlist_args, validate=True)
    @api.marshal_list_with(wishlist_model)
    def get(self):
        """ Returns all of the Wishlists """
        app.logger.info('Request to list Wishlists...')
        wishlists = []
        args = wishlist_args.parse_args()
        if args['customer_id']:
            app.logger.info('Filtering by customer: %s', args['customer_id'])
            wishlists = Wishlist.find_by_customer(args['customer_id'])
        # elif args['name']:
        #     app.logger.info('Filtering by name: %s', args['name'])
        #     wishlists = Wishlist.find_by_name(args['name'])
        else:
            app.logger.info('Returning unfiltered list.')
            wishlists = Wishlist.all()
        results = [wishlist.serialize() for wishlist in wishlists]
        app.logger.info('[%s] Wishlists returned', len(results))
        return results, status.HTTP_200_OK


    #------------------------------------------------------------------
    # ADD A NEW WISHLIST
    #------------------------------------------------------------------
    @api.doc('create_wishlists')
    @api.response(400, 'The posted data was not valid')
    @api.expect(create_model, validate=True)
    @api.marshal_with(wishlist_model, code=201)
    def post(self):
        """
        Creates a Wishlist
        This endpoint will create a Wishlist based the data in the body that is posted
        """
        app.logger.info('Request to Create a Wishlist')
        wishlist = Wishlist()
        app.logger.debug('Payload = %s', api.payload)
        wishlist.deserialize(api.payload)
        wishlist.create()
        app.logger.info('Wishlist with new id [%s] created!', wishlist.id)
        location_url = api.url_for(WishlistResource, wishlist_id=wishlist.id, _external=True)
        return wishlist.serialize(), status.HTTP_201_CREATED, {'Location': location_url}

######################################################################
# RETRIEVE A WISHLIST
######################################################################
# @app.route("/wishlists/<int:wishlist_id>", methods=["GET"])
# def get_wishlists(wishlist_id):
#     """
#     Retrieve a single Wishlist

#     This endpoint will return a Wishlist based on it's id
#     """
#     app.logger.info("Request for wishlist with id: %s", wishlist_id)
#     wishlist = Wishlist.find(wishlist_id)
#     if not wishlist:
#         raise NotFound(
#             "Wishlist with id '{}' was not found.".format(wishlist_id))

#     app.logger.info("Returning wishlist: %s", wishlist.name)
#     return make_response(jsonify(wishlist.serialize()), status.HTTP_200_OK)


######################################################################
# UPDATE AN EXISTING WISHLIST
######################################################################


# @app.route("/wishlists/<int:wishlist_id>", methods=["PUT"])
# def update_pets(wishlist_id):
#     """
#     Update a Wishlist

#     This endpoint will update a wishlist based the body that is posted
#     """
#     app.logger.info("Request to update wishlist with id: %s", wishlist_id)
#     check_content_type("application/json")
#     wishlist = Wishlist.find(wishlist_id)
#     if not wishlist:
#         raise NotFound(
#             "Wishlist with id '{}' was not found.".format(wishlist_id))
#     updated_wishlist = Wishlist()
#     updated_wishlist.deserialize(request.get_json())
#     wishlist.name = updated_wishlist.name
#     wishlist.customer_id = updated_wishlist.customer_id
#     wishlist.save()

#     app.logger.info("Wishlist with ID [%s] updated.", wishlist.id)
#     return make_response(jsonify(wishlist.serialize()), status.HTTP_200_OK)


######################################################################
# DELETE A WISHLIST
######################################################################
# @app.route("/wishlists/<int:wishlist_id>", methods=["DELETE"])
# def delete_wishlists(wishlist_id):
#     """
#     Delete a Wishlist

#     This endpoint will delete a Wishlist based the id specified in the path
#     """
#     app.logger.info("Request to delete wishlist with id: %s", wishlist_id)
#     wishlist = Wishlist.find(wishlist_id)
#     if wishlist:
#         wishlist.delete()

#     app.logger.info("Wishlist with ID [%s] delete complete.", wishlist_id)
#     return make_response("", status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------
#                I T E M   M E T H O D S
# ---------------------------------------------------------------------


# ######################################################################
# # LIST ADDRESSES
# ######################################################################
# @app.route("/accounts/<int:account_id>/addresses", methods=["GET"])
# def list_addresses(account_id):
#     """ Returns all of the Addresses for an Account """
#     app.logger.info("Request for Account Addresses...")
#     account = Account.find_or_404(account_id)
#     results = [address.serialize() for address in account.addresses]
#     return make_response(jsonify(results), status.HTTP_200_OK)


######################################################################
#  PATH: /wishlists/<wishlist_id>/items
######################################################################
@api.route('/wishlists/<int:wishlist_id>/items')
@api.param('wishlist_id', 'The Wishlist identifier')
class ProductsCollections(Resource):
    """
    ProductsResource class
    Handles all interactions with Products in a Wishlist
    """
    @api.doc('create_products')
    @api.response(400, 'The posted data was not valid')
    @api.expect(create_product_model, validate=True)
    @api.marshal_with(product_model, code=201)
    def post(self,wishlist_id):
        # ADD A ITEM TO AN WISHLIST
        app.logger.info("Request to add an item to an wishlist")
        wishlist = Wishlist.find_or_404(wishlist_id)
        app.logger.info('Payload = %s', api.payload)

        product = Product()
        api.payload['wishlist_id'] = wishlist_id
        product.deserialize(api.payload)
        product.wishlist_id = wishlist_id
        # product.purchased = False
        product.create()

        wishlist.products.append(product)
        wishlist.save()
       
        app.logger.info('product with new id [%s] created!', product.id)
        location_url = api.url_for(ProductsResource, wishlist_id =wishlist_id, item_id=product.id, _external=True)

        return product.serialize(), status.HTTP_201_CREATED, {'Location': location_url}

    @api.doc('list_all_items')
    @api.response(200, 'items listed')
    def get(self, wishlist_id):
        """Returns all of items of a wishlist"""
        app.logger.info("Request for Wishlist Products...")
        wishlist = Wishlist.find_or_404(wishlist_id)
        results = [product.serialize() for product in wishlist.products]
        return results, status.HTTP_200_OK
#@app.route('/wishlists/<int:wishlist_id>/items', methods=['GET'])
#def list_items_wishlists(wishlist_id):
#    """Returns all of items of a wishlist"""
#    app.logger.info("Request for Wishlist Products...")
#    wishlist = Wishlist.find_or_404(wishlist_id)
#    results = [product.serialize() for product in wishlist.products]
#    return make_response(jsonify(results), status.HTTP_200_OK)
        
######################################################################
#  PATH: /wishlists/<wishlist_id>/items/<item_id>
######################################################################
@api.route('/wishlists/<int:wishlist_id>/items/<int:item_id>')
@api.param('wishlist_id', 'The Wishlist identifier')
@api.param('item_id', 'The Product identifier')
class ProductsResource(Resource):
    """
    ProductsResource class

    Allows the manipulation of items within a wishlist
    DELETE /wishlists/<wishlists_id>/items/<item_id> -  Deletes a Product with the id
    GET /wishlists/<wishlists_id>/items/<item_id> -  Returns a Product with the id
    """
    @api.doc('get_product')
    @api.response(404, 'Product or wishlist not found')
    @api.marshal_with(product_model)
    def get(self, wishlist_id, item_id):
        """
        Get an Product
        This endpoint returns just an product
        """
        app.logger.info(
            "Request to get an item with id: %s from wishlist with id: %s", item_id, wishlist_id)
        wishlist = Wishlist.find_or_404(wishlist_id)
        product = Product.find_or_404(item_id)
        return product.serialize(), status.HTTP_200_OK

    @api.doc('delete_product')
    @api.response(204, 'product deleted')
    def delete(self, wishlist_id, item_id):
        """
        Delete a Product
        """
        app.logger.info(
            "Request to delete product with id: %s from wishlist with id: %s", item_id, wishlist_id)
        product = Product.find(item_id)
        if product:
            product.delete()
        return make_response("", status.HTTP_204_NO_CONTENT)

    

# ######################################################################
# # DELETE AN ITEM FROM WISHLIST
# ######################################################################

# @app.route('/wishlists/<int:wishlist_id>/items/<int:item_id>', methods=['DELETE'])
# def delete_products(wishlist_id, item_id):
#     """
#     Delete an Product
#     """
#     app.logger.info(
#         "Request to delete product with id: %s from wishlist with id: %s", item_id, wishlist_id)
#     product = Product.find(item_id)
#     if product:
#         product.delete()
#     return make_response("", status.HTTP_204_NO_CONTENT)

# ######################################################################
# # RETRIEVE AN ITEM FROM WISHLIST
# ######################################################################


# @app.route('/wishlists/<int:wishlist_id>/items/<int:item_id>', methods=['GET'])
# def get_products(wishlist_id, item_id):
#     """
#     Get an Product
#     This endpoint returns just an product
#     """
#     app.logger.info(
#         "Request to get an item with id: %s from wishlist with id: %s", item_id, wishlist_id)
#     wishlist = Wishlist.find_or_404(wishlist_id)
#     product = Product.find_or_404(item_id)
#     message = product.serialize()
#     return make_response(jsonify(message), status.HTTP_200_OK)



# ######################################################################
# # Path: /wishlists/wishlist_id/items/item_id/purchase
# ######################################################################

@api.route('/wishlists/<int:wishlist_id>/items/<int:item_id>/purchase')
@api.param('wishlist_id', 'The Wishlist identifier')
@api.param('item_id', 'The Product identifier')
class PurchaseResource(Resource):
    """
    Purchase an Product
    This endpoint returns just an product
    """

    @api.doc('purchase_products')
    @api.response(404, 'Product not found')
    @api.response(409, 'The Product is not available for purchase')
    @api.marshal_with(product_model)
    def put(self, wishlist_id, item_id):
        app.logger.info(
            "Request to purchase product with id: %s from wishlist with id: %s", item_id, wishlist_id)
        product = Product.find(item_id)
        if not product:
            abort(status.HTTP_404_NOT_FOUND, 'Product with id [{}] was not found.'.format(item_id))
        if product.purchased is True :
            abort(status.HTTP_409_CONFLICT, 'Product with id [{}] is not available.'.format(item_id))
        product.purchased = True
        product.save()
        app.logger.info("Item [%s] with in Wishlist with ID [%s] purchased.",item_id, wishlist_id)
        return product.serialize(), status.HTTP_200_OK



######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################


def check_content_type(media_type):
    """Checks that the media type is correct"""
    content_type = request.headers.get("Content-Type")
    if content_type and content_type == media_type:
        return
    app.logger.error("Invalid Content-Type: %s", content_type)
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "Content-Type must be {}".format(media_type),
    )

def abort(error_code: int, message: str):
    """Logs errors before aborting"""
    app.logger.error(message)
    api.abort(error_code, message)