# ============ REACTIONS & ENGAGEMENT ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/articles/<article_id>/reactions', methods=['POST'])
@jwt_required()
def toggle_article_reaction(article_id):
    """Toggle a reaction on an article (like, love, celebrate)"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        data = request.get_json() or {}
        reaction_type = data.get('type')  # 'like', 'love', 'celebrate'
        
        if reaction_type not in ['like', 'love', 'celebrate']:
            return jsonify({'error': 'Invalid reaction type. Must be: like, love, or celebrate'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        current_user_id = get_jwt_identity()
        
        # Initialize reactions if not exists
        if 'reactions' not in article:
            article['reactions'] = {'like': [], 'love': [], 'celebrate': []}
        
        # Check if user already reacted with this type
        user_reactions = article.get('reactions', {})
        reaction_list = user_reactions.get(reaction_type, [])
        
        if current_user_id in reaction_list:
            # Remove reaction
            news_collection.update_one(
                {'_id': obj_id},
                {
                    '$pull': {f'reactions.{reaction_type}': current_user_id},
                    '$inc': {'reaction_count': -1}
                }
            )
            action = 'removed'
        else:
            # Add reaction (remove from other types first)
            for rtype in ['like', 'love', 'celebrate']:
                if rtype != reaction_type and current_user_id in user_reactions.get(rtype, []):
                    news_collection.update_one(
                        {'_id': obj_id},
                        {'$pull': {f'reactions.{rtype}': current_user_id}}
                    )
            
            news_collection.update_one(
                {'_id': obj_id},
                {
                    '$addToSet': {f'reactions.{reaction_type}': current_user_id},
                    '$inc': {'reaction_count': 1}
                }
            )
            action = 'added'
        
        # Get updated counts
        updated_article = news_collection.find_one({'_id': obj_id}, {'reactions': 1, 'reaction_count': 1})
        reactions = updated_article.get('reactions', {})
        
        cache.delete_memoized(get_news_feed)
        
        return jsonify({
            'message': f'Reaction {action}',
            'action': action,
            'reactions': {
                'like': len(reactions.get('like', [])),
                'love': len(reactions.get('love', [])),
                'celebrate': len(reactions.get('celebrate', []))
            },
            'total_reactions': updated_article.get('reaction_count', 0),
            'user_reaction': reaction_type if action == 'added' else None
        }), 200
        
    except Exception as e:
        app.logger.error(f"Toggle reaction error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/articles/<article_id>/reactions', methods=['GET'])
def get_article_reactions(article_id):
    """Get reactions for an article"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        article = news_collection.find_one({'_id': obj_id}, {'reactions': 1, 'reaction_count': 1})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        reactions = article.get('reactions', {})
        current_user_id = get_jwt_identity() if request.headers.get('Authorization') else None
        user_reaction = None
        
        if current_user_id:
            for rtype in ['like', 'love', 'celebrate']:
                if current_user_id in reactions.get(rtype, []):
                    user_reaction = rtype
                    break
        
        return jsonify({
            'reactions': {
                'like': len(reactions.get('like', [])),
                'love': len(reactions.get('love', [])),
                'celebrate': len(reactions.get('celebrate', []))
            },
            'total_reactions': article.get('reaction_count', 0),
            'user_reaction': user_reaction
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get reactions error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/articles/<article_id>/bookmark', methods=['POST'])
@jwt_required()
def toggle_bookmark(article_id):
    """Toggle bookmark on an article"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        bookmarked_articles = user.get('bookmarked_articles', [])
        
        # Convert article_id string to ObjectId for consistent comparison
        if obj_id in bookmarked_articles:
            # Remove bookmark
            db.users.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$pull': {'bookmarked_articles': obj_id}}
            )
            action = 'removed'
        else:
            # Add bookmark
            db.users.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$addToSet': {'bookmarked_articles': obj_id}}
            )
            action = 'added'
        
        return jsonify({
            'message': f'Bookmark {action}',
            'action': action,
            'is_bookmarked': action == 'added'
        }), 200
        
    except Exception as e:
        app.logger.error(f"Toggle bookmark error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/user/bookmarks', methods=['GET'])
@jwt_required()
def get_bookmarked_articles():
    """Get user's bookmarked articles"""
    try:
        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        bookmarked_article_ids = user.get('bookmarked_articles', [])
        
        if not bookmarked_article_ids:
            return jsonify({
                'bookmarks': [],
                'total': 0
            }), 200
        
        # Get articles
        articles = list(news_collection.find({
            '_id': {'$in': bookmarked_article_ids},
            'status': 'approved'
        }).sort('submitted_at', DESCENDING))
        
        # Enrich with submitter info
        for article in articles:
            enrich_article_submitter(article)
        
        return jsonify({
            'bookmarks': serialize_doc(articles),
            'total': len(articles)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get bookmarks error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/articles/<article_id>/view', methods=['POST'])
def track_article_view(article_id):
    """Track article view (increment view count and unique viewers)"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        # Get user ID if authenticated (optional)
        user_id = None
        try:
            if request.headers.get('Authorization'):
                user_id = get_jwt_identity()
        except:
            pass
        
        # Initialize views and unique_viewers if not exists
        update_query = {'$inc': {'views': 1}}
        
        if user_id:
            # Add to unique viewers if not already there
            unique_viewers = article.get('unique_viewers', [])
            if user_id not in unique_viewers:
                update_query['$addToSet'] = {'unique_viewers': user_id}
        
        news_collection.update_one({'_id': obj_id}, update_query)
        
        # Get updated view count
        updated_article = news_collection.find_one({'_id': obj_id}, {'views': 1, 'unique_viewers': 1})
        
        return jsonify({
            'message': 'View tracked',
            'views': updated_article.get('views', 0),
            'unique_viewers': len(updated_article.get('unique_viewers', []))
        }), 200
        
    except Exception as e:
        app.logger.error(f"Track view error: {str(e)}")
        return jsonify({'error': str(e)}), 500
