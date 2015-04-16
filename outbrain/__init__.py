from dateutil.parser import parse
from datetime import datetime, timedelta
import requests
import simplejson as json
import yaml

class OutbrainAmplifyApi(object):

    def __init__(self, outbrain_config=None):
        if not outbrain_config:
            outbrain_config = yaml.load(open('outbrain.yml', 'r'))
        self.user = outbrain_config['user']
        self.password = outbrain_config['password']
        self.base_url = outbrain_config['base_url']
        self.token = self.get_token(self.user, self.password)

    def _request(self, path, params={}):
        url = self.base_url + path
        r = requests.get(url, headers={'OB-TOKEN-V1': self.token},
            params=params) 
        return json.loads(r.text)

    def get_token(self, user, password):
        token_url = self.base_url + '/login'
        basic_auth = requests.auth.HTTPBasicAuth(user, password)
        r = requests.get(token_url, auth=basic_auth)
        results = json.loads(r.text)
        return results['OB-TOKEN-V1']

    #----------------------------------------------------------------------------------------------
    # Methods to acquire marketer information
    #----------------------------------------------------------------------------------------------
    def get_marketer(self, marketer_id):
        path = 'marketers/{0}'.format(marketer_id)
        result = self._request(path)
        return result

    def get_marketers(self):
        path = 'marketers'
        results = self._request(path)
        return results['marketers']

    def get_all_marketer_ids(self):
        return [m for m in self._yield_all_marketer_ids()]

    def _yield_all_marketer_ids(self):
        marketers = self.get_marketers()
        for m in marketers:
            yield m

    #----------------------------------------------------------------------------------------------
    # Methods to acquire budget information
    #----------------------------------------------------------------------------------------------
    def get_budget(self, budget_id):
        path = 'budgets/{0}'.format(budget_id)
        result = self._request(path)
        return result

    def get_budgets_per_marketer(self, marketing_ids=[]):
        budgets = {}
        # marketing_ids = marketing_ids or 
        for marketing_id in marketing_ids:
            path = '/marketers/{0}/budgets'.format(marketing_id)
            results = self._request(path)
            marketer_budgets = results['budgets']
            budgets[marketing_id] = marketer_budgets
        return budgets

    #----------------------------------------------------------------------------------------------
    # Methods to acquire campaign information
    #----------------------------------------------------------------------------------------------
    def get_campaign(self, campaign_id):
        path = 'campaigns/' + campaign_id
        result = self._request(path)
        return result

    def get_all_campaign_ids(self):
        return [c for c in self._yield_all_campaign_ids()]

    def _yield_all_campaign_ids(self):
        marketers = self.get_marketers()
        marketer_ids = [m['id'] for m in marketers]

        marketer_campaigns = self.get_campaigns_per_marketer(marketer_ids)
        for m in marketer_campaigns.keys():
            for c in marketer_campaigns[m]:
                yield c['id']

    def get_campaigns_per_budget(self, budget_ids):
        campaigns = {}
        for budget_id in budget_ids:
            path = 'budgets/{0}/campaigns'.format(budget_id)
            results = self._request(path)            
            budget_campaigns = results['campaigns']
            campaigns[budget_id] = budget_campaigns
        return campaigns

    def get_campaigns_per_marketer(self, marketing_ids, include_archived=True):
        campaigns = {}
        for marketing_id in marketing_ids:
            path = 'marketers/{0}/campaigns'.format(marketing_id)
            params = {'includeArchived': 'true' if include_archived else 'false'}
            results = self._request(path, params)            
            marketer_campaigns = results['campaigns']
            campaigns[marketing_id] = marketer_campaigns
        return campaigns

    #----------------------------------------------------------------------------------------------
    # Methods to acquire performance information
    #----------------------------------------------------------------------------------------------
    def get_publisher_performace_per_marketer(self, marketer_ids, start_day, end_day):
        performance = dict()
        for m in marketer_ids:
            performance[m] = self.get_publisher_performace_for_marketer(marketer_id, start_day, end_day)
        return performance

    def get_publisher_performace_for_marketer(self, marketer_id, start_day, end_day):
        start = start_day.strftime('%Y-%m-%d')
        end = end_day.strftime('%Y-%m-%d')
        return [perf for perf in self._yield_publisher_performace_for_marketer(marketer_id, start, end)]

    def _yield_publisher_performace_for_marketer(self, marketer_id, start, end):
        offset = 0
        performance = self._page_publisher_performace_for_marketer(marketer_id, start, end, 50, offset)
        while performance:
            for perf in performance:
                yield perf

            offset += len(performance)
            performance = self._page_publisher_performace_for_marketer(marketer_id, start, end, 50, offset)

    def _page_publisher_performace_for_marketer(self, marketer_id, start, end, limit, offset):
        path = 'marketers/{0}/performanceByPublisher'.format(marketer_id)
        params = {'limit': limit,
                  'offset': offset,
                  'to': start.strftime('%Y-%m-%d'),
                  'from': end.strftime('%Y-%m-%d')}
        result = self._request(path, params)
        return result.get('details', [])

    # def get_daily_performance(self, promoted_link_ids, start_day=None, end_day=None):
    #     if not end_day:
    #         end_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)    
    #     if not start_day:
    #         start_day = end_day - timedelta(days=1)
    #     
    #     daily_link_performance = {}
    #     for promoted_link_id in promoted_link_ids:
    #         path = 'promotedLinks/' + promoted_link_id + '/performanceByDay/'
    #         
    #         daily_link_performance[promoted_link_id] = {}
    #         current_day = start_day
    #         while current_day < end_day:
    #             next_day = current_day + timedelta(days=1)
    #             params = {'from': current_day.date(), 'to': next_day.date()}
    #             results = self._request(path, params)
    #             
    #             metrics = results['overallMetrics']
    #             if metrics['cost'] + metrics['impressions'] + metrics['clicks'] > 0:
    #                 daily_link_performance[promoted_link_id][current_day] = metrics
    #             current_day += timedelta(days=1)
    #     return daily_link_performance

    #----------------------------------------------------------------------------------------------
    # Methods to acquire promoted link information
    #----------------------------------------------------------------------------------------------
    def get_promoted_links_per_campaign(self, campaign_ids=[], enabled=None, statuses=[]):
        campaign_ids = campaign_ids or self.get_all_campaign_ids()
        promoted_links = dict()
        for c in campaign_ids:
            promoted_links[c] = self.get_promoted_links_for_campaign(c, enabled, statuses)
        return promoted_links

    def get_promoted_links_for_campaign(self, campaign_id, enabled=None, statuses=[]):
        return [link for link in self._yield_promoted_links_for_campaign(campaign_id, enabled, statuses)]

    def _yield_promoted_links_for_campaign(self, campaign_id, enabled=None, statuses=[]):
        offset = 0
        promoted_links = self._page_promoted_links_for_campaign(campaign_id, enabled, statuses, 50, offset)
        while promoted_links:
            for pl in promoted_links:
                yield pl

            offset += len(promoted_links)
            promoted_links = self._page_promoted_links_for_campaign(campaign_id, enabled, statuses, 50, offset)

    def _page_promoted_links_for_campaign(self, campaign_id, enabled, statuses, limit, offset):
        path = 'campaigns/{0}/promotedLinks'.format(campaign_id)
        params = {'limit': limit,
                  'offset': offset}

        if enabled is not None:
            params['enabled'] = 'true' if enabled else 'false'
        if statuses:
            params['statuses'] = ','.join(statuses)

        return self._request(path, params).get('promotedLinks', [])

    #----------------------------------------------------------------------------------------------
    # Other methods
    #----------------------------------------------------------------------------------------------
    def get_currencies(self):
        results = self._request('currencies')
        return results.get('currencies', [])
