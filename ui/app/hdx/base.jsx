import React from 'react';

import createHistory from 'history/createHashHistory';
import { Col, Row } from 'react-bootstrap';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { Route } from 'react-router';
import { ConnectedRouter, routerReducer, routerMiddleware } from 'react-router-redux';
import { createStore, combineReducers, applyMiddleware } from 'redux';
import createLogger from 'redux-logger';
import thunk from 'redux-thunk';

import ExportAOI from './components/ExportAOI';
import MapListView from './components/MapListView';
import HDXExportRegionForm from './components/HDXExportRegionForm';
import HDXExportRegionList from './components/HDXExportRegionList';
import reducers from './reducers/';

const history = createHistory();

const store = createStore(
  combineReducers({
    ...reducers,
    router: routerReducer
  }),
  applyMiddleware(routerMiddleware(history), thunk, createLogger())
);

ReactDOM.render(
  <Provider store={store}>
    {/* ConnectedRouter will use the store from Provider automatically */}
    <ConnectedRouter history={history}>
      <Row style={{height: '100%'}}>
        <Col xs={6} style={{height: '100%', overflowY: 'scroll'}}>
          <Route exact path='/' component={HDXExportRegionList} />
          <Route path='/new' component={HDXExportRegionForm} />
          <Route path='/edit/:id' component={HDXExportRegionForm} />
        </Col>
        <Col xs={6} style={{height: '100%'}}>
          <Route exact path='/' component={MapListView} />
          <Route path='/new' component={ExportAOI} />
          <Route path='/edit/:id' component={ExportAOI} />
        </Col>
      </Row>
    </ConnectedRouter>
  </Provider>,
  document.getElementById('root')
);
