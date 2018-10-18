
import React from 'react';
import { Text, Group, Path, Image } from 'react-konva';
import PropTypes from 'prop-types';

import upsimg from '../../../images/ups_monitor_2.png';
import c14 from '../../../images/c14.svg';
import Socket from '../common/Socket';

import colors from '../../../styles/colors';
import paths from '../../../styles/paths';

/**
 * Draw Ups graphics
 */
export default class Ups extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      selectedSocketKey: -1,
      x: props.x,
      y: props.y,

      upsMonitorImg: null,
      c14Img: null
    };

    this.selectSocket = this.selectSocket.bind(this);
    this.inputSocketPos = {x: 254, y: 5};
  }

  componentDidMount() {
    const upsMonitorImg = new window.Image();
    const c14Img = new window.Image();

    upsMonitorImg.src = upsimg;
    c14Img.src = c14;

    upsMonitorImg.onload = () => { this.setState({ upsMonitorImg }); };
    c14Img.onload = () => { this.setState({ c14Img }); };
  }


  /** Notify Parent of Selection */
  handleClick = () => {
    this.refs.ups.setZIndex(100);
    this.props.onElementSelection(this.props.assetId, this.props.asset);
  };

  /** Notify top-lvl Component that PDU-Outlet was selected*/
  selectSocket = (ckey) => {
    this.setState({ selectedSocketKey: ckey });
    this.props.onElementSelection(ckey, this.props.asset.children[ckey]);
  }

  getOutputCoordinates = (center=true) => {

    let chidCoord = {};
    let x = 250 + center?this.state.c14Img.width*0.5:0;
    let y = 150 + center?this.state.c14Img.height*0.5:0;

    Object.keys(this.props.asset.children).forEach((key, i) => {
      chidCoord[key] = {x, y};
      x += 100;

      if (i == 4) {
        y += 100;
        x = 250;
      }
    });

    return chidCoord;
  }

  updateUpsPos = (s) => {
    const coord = {
      x: s.target.attrs.x,
      y: s.target.attrs.y,
      inputConnections: [
        {
          x: this.inputSocketPos.x + this.state.c14Img.width*0.5,
          y: this.inputSocketPos.y + this.state.c14Img.height*0.5,
        }
      ],
      outputConnections: this.getOutputCoordinates(),
    };

    this.setState(coord);
    this.props.onPosChange(this.props.assetId, coord);
  }

  render() {

    let outputSockets = [];
    const inputSocket = <Image image={this.state.c14Img} x={this.inputSocketPos.x} y={this.inputSocketPos.y}/>;

    const upsName = this.props.asset.name ? this.props.asset.name:'ups';
    let chargeBar = "|||||||||||||||||||||||||||||||||||";
    chargeBar = this.props.asset.battery === 1000 ? chargeBar: chargeBar.substring(chargeBar.length * (1-this.props.asset.battery * 0.001));

    const asset = this.props.asset;
    let y=140;
    let x=255;
    let socketIndex = 0;
    // Initialize outlets that are part of the device
    for (const ckey of Object.keys(asset.children)) {

      asset.children[ckey].name = `[${ckey}]`;
      outputSockets.push(
        <Socket
          y={y}
          x={x}
          key={ckey}
          onElementSelection={() => { this.selectSocket(ckey); }}
          draggable={false}
          asset={asset.children[ckey]}
          assetId={ckey}
          selected={this.state.selectedSocketKey === ckey && this.props.nestedComponentSelected}
          powered={this.props.asset.status !== 0}
          parentSelected={this.props.selected}
          hideName={true}
          onPosChange={this.props.onPosChange}
        />
      );
      x += 100;
      socketIndex++;
      if (socketIndex == 4) {
        y += 100;
        x = 255;
      }
    }


    return (
      <Group
        draggable="true"
        onDragMove={this.updateUpsPos.bind(this)}
        x={this.state.x}
        y={this.state.y}
        ref="ups"
      >


        {/* Draw Ups as SVG path */}
        <Path data={paths.ups}
          strokeWidth={0.4}
          stroke={this.props.selected ? colors.selectedAsset : colors.deselectedAsset}
          fill={'white'}
          scale={{x: 4, y: 4}}
          y={-575}
          onClick={this.handleClick.bind(this)}
        />

        {/* UPS Label */}
        <Text y={-125} x={230} text={upsName} fontSize={18}  fontFamily={'Helvetica'} />

        {/* UPS Display */}
        <Group
          x={345}
          y={-50}
        >
          <Image
              image={this.state.upsMonitorImg}
              onClick={this.handleClick}
          />
          <Group y={50} x={18}>
            <Text
              text={`Output ${this.props.asset.status?'ON':'OFF'}`}
              fontFamily={'DSEG14Modern'}
              fontSize={16}
              fill={this.props.asset.status?'white':'grey'}
            />

            <Text y={30}
              text={`Batt ${Math.floor(this.props.asset.battery/10)}%`}
              fontFamily={'DSEG14Modern'}
              fontSize={16}
              fill={this.props.asset.status?'white':'grey'}
            />
            <Text y={30} x={110}
              text={chargeBar}

              fontSize={16}
              fill={this.props.asset.status?'white':'grey'}
            />
          </Group>
        </Group>

        {/* IO Sockets */}
        {inputSocket}
        {outputSockets}

      </Group>
    );
  }
}

Ups.propTypes = {
  name: PropTypes.string,
  x: PropTypes.number, // X position of the asset
  y: PropTypes.number, // Y position of the asset
  onPosChange: PropTypes.func.isRequired, // called on asset position change
  asset: PropTypes.object.isRequired, // Asset Details
  assetId: PropTypes.string.isRequired, // Asset Key
  selected: PropTypes.bool.isRequired, // Asset Selected by a user
  onElementSelection: PropTypes.func.isRequired, // Notify parent component of selection
  nestedComponentSelected: PropTypes.bool.isRequired, // One of the UPS outlets are selected
};
