import React from 'react';
import styled from 'styled-components';

interface CardProps {
  isSearched?: boolean;
  isModalOpen?: boolean;
}

const Card = ({ isSearched = false, isModalOpen = false }: CardProps) => {
  return (
    <StyledWrapper $isSearched={isSearched} $isModalOpen={isModalOpen}>
      <div className="box">
        <span />
        <div className="content">
          <h1>QuantRift</h1>
        </div>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div<{ $isSearched: boolean; $isModalOpen: boolean }>`
  filter: ${props => props.$isModalOpen ? 'blur(4px)' : 'none'};
  opacity: ${props => props.$isModalOpen ? 0.5 : 1};
  transition: filter 0.3s ease, opacity 0.3s ease;
  pointer-events: ${props => props.$isModalOpen ? 'none' : 'auto'};
  
  .box {
   position: relative;
   width: ${props => props.$isSearched ? '400px' : '800px'};
   height: ${props => props.$isSearched ? '100px' : '180px'};
   display: flex;
   justify-content: center;
   align-items: center;
   transition: 0.5s;
   z-index: 1;
  }

  .box::before {
   content: ' ';
   position: absolute;
   top: 0;
   left: ${props => props.$isSearched ? '50px' : '150px'};
   right: ${props => props.$isSearched ? '50px' : '150px'};
   width: auto;
   height: 100%;
   text-decoration: none;
   background: #fff;
   border-radius: 8px;
   transform: skewX(15deg);
   transition: 0.5s;
  }

  .box::after {
   content: '';
   position: absolute;
   top: 0;
   left: ${props => props.$isSearched ? '50px' : '150px'};
   right: ${props => props.$isSearched ? '50px' : '150px'};
   width: auto;
   height: 100%;
   background: #fff;
   border-radius: 8px;
   transform: skewX(15deg);
   transition: 0.5s;
   filter: blur(10px);
   opacity: 0.6;
  }

  .box:hover:before,
  .box:hover:after {
   transform: skewX(0deg) scaleX(1.3);
  }

  .box:before,
  .box:after {
   background: linear-gradient(300deg, #E07B39, #D8709F, #4A90C0)
  }

  .box span {
   display: none;
  }

  .box .content {
   position: relative;
   width: ${props => props.$isSearched ? '350px' : '700px'};
   height: ${props => props.$isSearched ? '80px' : '150px'};
   padding: 20px 40px;
   background: rgba(255, 255, 255, 0.05);
   backdrop-filter: blur(2px);
   box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
   border-radius: 8px;
   z-index: 1;
   transform: 0.5s;
   color: #fff;
   display: flex;
   justify-content: center;
   align-items: center;
  }

  .box .content h1 {
   font-family: "PaybAck", sans-serif;
   font-size: ${props => props.$isSearched ? '3rem' : '9rem'};
   font-weight: 400;
   letter-spacing: 0.02em;
   color: #fff;
   margin: 0;
   text-shadow: 0 2px 8px rgba(255, 255, 255, 0.3);
  }`;

export default Card;

